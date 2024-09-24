from collections import defaultdict
import json
import math
from typing import Any, Callable, TypeVar
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import func, select, delete
from app.schemas.rating import (
    ChoosePayloadSchema,
    ChooseResponseSchema,
    RatingChoiceResponseSchema,
)
from app.services import BaseService, ModelRequests
from app.models.tests import Competition, CompetitionItem, Rating, RatingChoice
import random
from app.services.competition_item import CompetitionItemService
from app.services.rating_choice import RatingChoiceService


_T = TypeVar("_T", bound=Any)


class RatingService(BaseService, ModelRequests[Rating]):
    model = Rating

    _rating_choice_service: RatingChoiceService = None
    _competition_item_service: CompetitionItemService = None

    @property
    def rating_choice_service(self):
        if self._rating_choice_service is None:
            self._rating_choice_service = RatingChoiceService(
                self.session, self.redis, self._token
            )
        return self._rating_choice_service

    @property
    def competition_item_service(self):
        if self._competition_item_service is None:
            self._competition_item_service = CompetitionItemService(
                self.session, self.redis, self._token
            )
        return self._competition_item_service

    cache_key_items = "cache:RatingService:available_items:{rating_id}"
    cache_grid = "cache:RatingService:grid:{rating_id}"
    cache_expire = 3600

    class CustomJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            try:
                return super().default(obj)
            except TypeError as e:
                if isinstance(obj, UUID):
                    return str(obj)
                raise e
    
    class CustomJSONDecoder(json.JSONDecoder):
        def decode(self, s: str) -> Any:
            obj = super().decode(s)
            if isinstance(obj, str):
                try:
                    return UUID(obj)
                except ValueError:
                    return obj
            return obj

    async def _get_available_items_ids(self, rating_id: UUID, use_cache=True) -> list[UUID]:
        if use_cache:
            cache_key = self.cache_key_items.format(rating_id=rating_id)

            cached_result = await self.redis.get(cache_key)

            if cached_result:
                return json.loads(cached_result, cls=self.CustomJSONDecoder)

        subquery = (
            select(RatingChoice.winner_id)
            .join(Rating, Rating.id == RatingChoice.rating_id)
            .filter(
                RatingChoice.rating_id == rating_id,
                RatingChoice.stage == Rating.stage,
            )
            .union_all(
                select(RatingChoice.looser_id)
                .distinct()
                .filter(
                    RatingChoice.rating_id == rating_id,
                    RatingChoice.looser_id.isnot(None),
                )
            )
            .subquery()
        )
        stmt = (
            select(CompetitionItem.id)
            .join(Rating, Rating.competition_id == CompetitionItem.competition_id)
            .filter(
                Rating.id == rating_id,
                CompetitionItem.competition_id == Rating.competition_id,
                CompetitionItem.id.not_in(select(subquery)),
            )
        )
        ids: list[UUID] = (await self.session.scalars(stmt)).all()
        return ids

    async def _cache_ids(self, ids: list[UUID], cache_key: str):
        await self.redis.setex(
            cache_key,
            self.cache_expire,
            json.dumps(ids, cls=RatingService.CustomJSONEncoder),
        )

    def _new_rating_choice(self, rating: Rating, ids: list[UUID]):
        if not ids:
            return None
        winner_id = ids.pop(random.randint(0, len(ids) - 1))
        looser_id = ids.pop(random.randint(0, len(ids) - 1)) if ids else None
        return RatingChoice(
            rating_id=rating.id,
            winner_id=winner_id,
            looser_id=looser_id,
            stage=rating.stage,
        )

    @staticmethod
    def _get_nth_element(lst: list[_T], n: int):
        if n < 0:
            return None
        try:
            return lst[n]
        except IndexError:
            return None

    async def get_last_choice(self, id: UUID):
        """
        Get the last choice of the rating with the given id.

        Args:
            id (UUID): The id of the rating.

        Returns:
            RatingChoiceResponseSchema: The last rating choice.
        """

        rating = await self.get(id=id)
        rating_choice = await self.rating_choice_service.get(id=rating.choices[-1])

        items = [rating_choice.winner_id]
        if rating_choice.looser_id:
            items.append(rating_choice.looser_id)
            items.sort(key=lambda x: str(x))
        return RatingChoiceResponseSchema(
            id=rating_choice.id,
            items=items,
            stage=rating_choice.stage,
            prev=self._get_nth_element(
                rating.choices, rating.choices.index(rating_choice.id) - 1
            ),
            round=len(rating.choices),
        )

    async def get_choice(self, rating_id: UUID, choice_id: UUID):
        """
        Get a rating choice by id.

        Args:
            rating_id (UUID): The id of the rating.
            choice_id (UUID): The id of the choice to retrieve.

        Returns:
            RatingChoiceResponseSchema: The rating choice.
        """

        rating = await self.get(id=rating_id)
        rating_choice = await self.rating_choice_service.get(id=choice_id)

        items = [rating_choice.winner_id]
        if rating_choice.looser_id:
            items.append(rating_choice.looser_id)
            items.sort(key=lambda x: str(x))

        return RatingChoiceResponseSchema(
            id=rating_choice.id,
            items=items,
            stage=rating_choice.stage,
            next=self._get_nth_element(
                rating.choices, rating.choices.index(rating_choice.id) + 1
            ),
            prev=self._get_nth_element(
                rating.choices, rating.choices.index(rating_choice.id) - 1
            ),
            round=rating.choices.index(choice_id) + 1,
            winner_id=rating_choice.winner_id
            if rating_choice.id != rating.choices[-1]
            else None,
        )

    async def start(self, competition_id: UUID):
        """
        Start a new rating for a competition.

        Args:
            competition_id (UUID): The id of the competition.

        Returns:
            str: The id of the new rating.
        """
        stmt = select(Competition).filter(
            Competition.id == competition_id,
            Competition.published == True,  # noqa: E712
        )
        competition = await self.session.scalar(stmt)

        if not competition:
            raise HTTPException(status_code=404, detail="Competition not found")

        rating = Rating(
            competition_id=competition_id,
            user_id=self.token.sub,
        )
        self.session.add(rating)

        await self.session.flush()
        await self.session.refresh(rating)

        ids = await self._get_available_items_ids(rating.id, use_cache=False)
        new_choice = self._new_rating_choice(rating, ids)
        self.session.add(new_choice)

        await self.session.flush()
        await self.session.refresh(rating)
        await self.session.refresh(new_choice)

        rating.choices.append(new_choice.id)
        rating_id = str(rating.id)

        await self.session.commit()
        await self._cache_ids(ids, self.cache_key_items.format(rating_id=rating.id))
        return rating_id

    async def refresh(self, id: UUID, choice_id: UUID):
        """
        Refresh a rating by removing all the choices from the current choice onward
        and generating a new one.

        Args:
            id (UUID): The id of the rating.
            choice_id (UUID): The id of the choice to refresh from.

        Returns:
            StartRatingResponseSchema: The rating with the new choice.
        """
        rating = await self.get(id=id, user_id=self.token.sub)

        if rating.is_refreshed:
            raise HTTPException(status_code=403, detail="Rating is refreshed")

        rating_choice = await self.rating_choice_service.get(id=choice_id, rating_id=id)

        idx = rating.choices.index(rating_choice.id)
        if (len(rating.choices) > 1) and (len(rating.choices) > idx + 1):
            stmt = delete(RatingChoice).filter(
                RatingChoice.rating_id == rating.id,
                RatingChoice.id.in_(rating.choices[idx + 1 :]),
            )
            await self.session.execute(stmt)
            rating.choices = rating.choices[: idx + 1]

            await self.session.flush()
            await self.session.refresh(rating)

        ids = await self._get_available_items_ids(rating.id, use_cache=False)
        ids.append(rating_choice.winner_id)
        if rating_choice.looser_id:
            ids.append(rating_choice.looser_id)
        rating_choice.winner_id = ids.pop(random.randint(0, len(ids) - 1))
        rating_choice.looser_id = (
            ids.pop(random.randint(0, len(ids) - 1)) if ids else None
        )

        items = [rating_choice.winner_id]
        if rating_choice.looser_id:
            items.append(rating_choice.looser_id)
            items.sort(key=lambda x: str(x))

        cur_choice = RatingChoiceResponseSchema(
            id=rating_choice.id,
            items=items,
            stage=rating_choice.stage,
            prev=self._get_nth_element(
                rating.choices, rating.choices.index(rating_choice.id) - 1
            ),
            round=len(rating.choices),
        )
        cache_key = self.cache_key_items.format(rating_id=rating.id)
        await self.session.commit()

        await self._cache_ids(ids, cache_key)
        return cur_choice

    async def choose(self, id: UUID, choice_id: UUID, payload: ChoosePayloadSchema):
        """
        Choose a winner and looser for a rating choice.

        Args:
            id: The id of the rating.
            choice_id: The id of the rating choice.
            payload: The payload with the winner and looser item ids.

        Returns:
            A ChooseResponseSchema with the next rating choice and ended boolean.
        """
        rating = await self.get(id=id, user_id=self.token.sub)

        choice = await self.rating_choice_service.get(id=choice_id)

        if payload.winner_id not in {choice.winner_id, choice.looser_id}:
            raise HTTPException(400, "Invalid request")
        if choice.winner_id != payload.winner_id:
            choice.winner_id, choice.looser_id = choice.looser_id, choice.winner_id

        if rating.choices[-1] == choice_id:
            ids = await self._get_available_items_ids(rating.id)
            next_coice = self._new_rating_choice(rating, ids)
            if not next_coice:
                rating.stage += 1
                rating.is_refreshed = False
                rating.choices = []
                await self.session.flush()
                await self.session.refresh(rating)

                ids = await self._get_available_items_ids(rating.id, use_cache=False)
                next_coice = self._new_rating_choice(rating, ids)
                if not next_coice.looser_id:
                    rating.ended = True
                    await self.session.commit()
                    await self.redis.delete(
                        self.cache_key_items.format(rating_id=rating.id)
                    )
                    return ChooseResponseSchema(ended=True)

            self.session.add(next_coice)
            await self.session.flush()
            await self.session.refresh(next_coice)
            rating.choices.append(next_coice.id)
        else:
            next_coice = await self.session.get(
                RatingChoice, rating.choices[rating.choices.index(choice_id) + 1]
            )

        await self.session.commit()
        await self.session.refresh(rating)
        await self.session.refresh(next_coice)

        try:
            await self._cache_ids(ids, self.cache_key_items.format(rating_id=rating.id))
        except UnboundLocalError:
            pass

        items = [next_coice.winner_id]
        if next_coice.looser_id:
            items.append(next_coice.looser_id)
            items.sort(key=lambda x: str(x))

        next_choice_schema = RatingChoiceResponseSchema(
            id=next_coice.id,
            stage=next_coice.stage,
            items=items,
            round=rating.choices.index(next_coice.id) + 1,
            next=self._get_nth_element(
                rating.choices, rating.choices.index(next_coice.id) + 1
            ),
            prev=self._get_nth_element(
                rating.choices, rating.choices.index(next_coice.id) - 1
            ),
            winner_id=next_coice.winner_id
            if next_coice.id != rating.choices[-1]
            else None,
        )

        return ChooseResponseSchema(next_choice=next_choice_schema, ended=rating.ended)

    async def get_rounds_total(self, id: UUID):
        rating = await self.get(id=id, user_id=self.token.sub)

        stmt = select(func.count(CompetitionItem.id)).filter(
            CompetitionItem.competition_id == rating.competition_id
        )
        items_total: int = await self.session.scalar(stmt)
        return math.ceil(items_total / (2 ** (rating.stage)))

    async def get_stage_items(self, id: UUID):
        subquery = (
            select(RatingChoice.winner_id)
            .join(Rating, Rating.id == RatingChoice.rating_id)
            .filter(
                RatingChoice.rating_id == id,
                RatingChoice.stage == Rating.stage,
            )
            .union_all(
                select(RatingChoice.looser_id)
                .join(Rating, Rating.id == RatingChoice.rating_id)
                .filter(
                    RatingChoice.rating_id == id,
                    RatingChoice.stage == Rating.stage,
                    RatingChoice.looser_id.isnot(None),
                )
            )
            .subquery()
        )
        stmt = (
            select(CompetitionItem)
            .filter(
                CompetitionItem.id.in_(await self._get_available_items_ids(id))
                | CompetitionItem.id.in_(select(subquery))
            )
            .order_by(CompetitionItem.created_at)
        )
        items = (await self.session.scalars(stmt)).all()
        return items

    async def get_grid(self, id: UUID) -> list[list[tuple[UUID, UUID | None]]]:
        cache_key = self.cache_grid.format(rating_id=id)
        cached_result = await self.redis.get(cache_key)
        if cached_result:
            return json.loads(cached_result, cls=self.CustomJSONDecoder)
        
        stmt = (
            select(RatingChoice.stage, RatingChoice.winner_id, RatingChoice.looser_id)
            .filter(RatingChoice.rating_id == id)
            .order_by(RatingChoice.created_at)
        )

        result: list[tuple[int, UUID, UUID | None]] = (
            await self.session.execute(stmt)
        ).all()
        response_dict = defaultdict(list[tuple[UUID, UUID | None]])
        for stage, winner, looser in result:
            response_dict[stage].append((winner, looser))

        response = list(response_dict.values())
        for i in range(len(response) - 1, 0, -1):
            cur_stage_choices = response[i]
            prev_stage_choices = response[i - 1]

            choice_index = 0
            for cur_choice in cur_stage_choices:
                winner_index = next(
                    (
                        x
                        for x, item in enumerate(prev_stage_choices)
                        if item[0] == cur_choice[0]
                    ),
                )
                prev_stage_choices[choice_index], prev_stage_choices[winner_index] = (
                    prev_stage_choices[winner_index],
                    prev_stage_choices[choice_index],
                )
                choice_index += 1
                if cur_choice[1] is None:
                    continue
                looser_index = next(
                    (
                        x
                        for x, item in enumerate(prev_stage_choices)
                        if item[0] == cur_choice[1]
                    ),
                )
                prev_stage_choices[choice_index], prev_stage_choices[looser_index] = (
                    prev_stage_choices[looser_index],
                    prev_stage_choices[choice_index],
                )
                choice_index += 1
        await self.redis.setex(
            cache_key,
            self.cache_expire,
            json.dumps(response, cls=RatingService.CustomJSONEncoder),
        )
        return response
