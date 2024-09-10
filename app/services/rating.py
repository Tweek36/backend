import json
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select, delete
from app.schemas.rating import (
    ChoosePayloadSchema,
    ChooseResponseSchema,
    RatingChoiceResponseSchema,
    StartRatingResponseSchema,
)
from app.services import BaseService, ModelRequests
from app.models.tests import Competition, CompetitionItem, Rating, RatingChoice
import random


class RatingService(BaseService, ModelRequests[Rating]):
    model = Rating

    cache_key_items = "cache:RatingService:available_items:{rating_id}"
    cache_expire = 3600

    class CustomJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            try:
                return super().default(obj)
            except TypeError as e:
                if isinstance(obj, UUID):
                    return str(obj)
                raise e

    async def _get_available_items_ids(self, rating_id: UUID, use_cache=True):
        if use_cache:
            cache_key = self.cache_key_items.format(rating_id=rating_id)

            cached_result = await self.redis.get(cache_key)

            if cached_result:
                return [UUID(i) for i in json.loads(cached_result)]

            rating = await self.session.get(Rating, rating_id)

        stmt = (
            select(CompetitionItem.id)
            .join(RatingChoice)
            .filter(
                RatingChoice.rating_id == rating_id,
                RatingChoice.stage == rating.stage,
                CompetitionItem.id != RatingChoice.winner_id,
                CompetitionItem.id != RatingChoice.looser_id,
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

    async def _delete_ids_cache(self, key: str):
        await self.redis.delete(key)

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

    async def get_rating_choice(self, **filters):
        stmt = select(RatingChoice).filter_by(**filters)
        data = await self.session.scalar(stmt)
        if not data:
            raise HTTPException(status_code=404, detail="RatingChoice not found")
        return data

    async def start(self, competition_id: UUID):
        """
        Start a rating session.

        Args:
            competition_id (UUID): id of the competition.

        Returns:
            StartRatingResponseSchema: response with rating_id and current choice.
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
            items=[],
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
        winner = await self.session.get(CompetitionItem, new_choice.winner_id)
        looser = (
            await self.session.get(CompetitionItem, new_choice.looser_id)
            if new_choice.looser_id
            else None
        )
        items = [winner]
        if looser:
            items.append(looser)

        items.sort()
        response = StartRatingResponseSchema(
            rating_id=rating.id,
            cur_choice=RatingChoiceResponseSchema(id=new_choice.id, items=items),
        )

        await self.session.commit()
        await self._cache_ids(ids, self.cache_key_items.format(rating_id=rating.id))
        return response

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
            raise HTTPException(status_code=400, detail="Rating is refreshed")

        stmt = select(RatingChoice).filter(
            RatingChoice.id == choice_id, RatingChoice.rating_id == id
        )
        cur_rating_choice = await self.session.scalar(stmt)

        if not cur_rating_choice:
            raise HTTPException(status_code=404, detail="RatingChoice not found. How?")

        idx = rating.choices.index(cur_rating_choice.id)

        stmt = delete(RatingChoice).filter(
            RatingChoice.rating_id == rating.id,
            RatingChoice.id.in_(rating.choices[idx:]),
        )
        await self.redis.delete()
        await self.session.execute(stmt)

        rating.choices = rating.choices[:idx]
        ids = self._get_available_items_ids(rating.id, use_cache=False)
        new_choice = self._new_rating_choice(rating, ids)
        self.session.add(new_choice)
        await self.session.flush()
        await self.session.refresh(new_choice)

        rating.choices.append(new_choice.id)
        await self.session.commit()
        await self.session.refresh(rating)
        await self.session.refresh(new_choice)

        cache_key = self.cache_key_items.format(rating_id=rating.id)
        await self._delete_ids_cache(cache_key)
        return StartRatingResponseSchema(rating_id=rating.id, cur_choice=new_choice)

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

        choice = await self.get_rating_choice(id=choice_id)

        if not {payload.winner_id, payload.looser_id}.issubset(
            {choice.winner_id, choice.looser_id}
        ):
            raise HTTPException(400, "Invalid request")

        choice.winner_id = payload.winner_id
        choice.looser_id = payload.looser_id

        if rating.choices[-1] == choice_id:
            ids = await self._get_available_items_ids(rating.id)
            next_coice = self._new_rating_choice(rating, ids)
            if not next_coice:
                rating.stage += 1
                rating.is_refreshed = False
                await self.session.flush()
                await self.session.refresh(rating)

                next_coice = self._new_rating_choice(rating, ids)
                if not next_coice.looser_id:
                    rating.ended = True
                    await self.session.commit()
                    return ChooseResponseSchema(ended=True)

            self.session.add(next_coice)
        else:
            next_coice = await self.session.get(
                RatingChoice, rating.choices[rating.choices.index(choice_id) + 1]
            )
        await self.session.commit()
        await self.session.refresh(rating)
        await self.session.refresh(next_coice)

        items = []
        items.append(await self.session.get(CompetitionItem, next_coice.winner_id))
        if next_coice.looser_id:
            items.append(await self.session.get(CompetitionItem, next_coice.looser_id))
            items.sort()
        next_choice_schema = RatingChoiceResponseSchema(
            id=next_coice.id, stage=rating.stage, items=items
        )
        return ChooseResponseSchema(next_choice=next_choice_schema, ended=rating.ended)
