from datetime import datetime
from typing import Annotated
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, declared_attr
from sqlalchemy import Integer, String, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY, TIMESTAMP
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
)
from app.models import created_at, updated_at, str_uniq, str_nullable, uuid_pk, int_pk
import uuid
from sqlalchemy.ext.mutable import MutableList


user_nullable_fk = Annotated[
    uuid.UUID,
    mapped_column(
        ForeignKey("user.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=True
    ),
]
user_fk = Annotated[
    uuid.UUID,
    mapped_column(
        ForeignKey("user.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False
    ),
]


class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return "".join(
            f'{c.lower() if i == 0 else "_" + c.lower() if c.isupper() and i > 0 and cls.__name__[i-1].islower() else c.lower()}'
            for i, c in enumerate(cls.__name__)
        )

    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]
    created_by: Mapped[user_nullable_fk]
    updated_by: Mapped[user_nullable_fk]


class User(Base):
    id: Mapped[uuid_pk]
    username: Mapped[str_uniq]
    email: Mapped[str_uniq]
    access_lvl: Mapped[int] = mapped_column(Integer, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)


class Competition(Base):
    id: Mapped[uuid_pk]
    user_id: Mapped[user_fk]
    title: Mapped[str_nullable]
    description: Mapped[str_nullable]
    category: Mapped[str] = mapped_column(String, nullable=False)
    image: Mapped[str] = mapped_column(String, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CompetitionItem(Base):
    id: Mapped[uuid_pk]
    competition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(Competition.id, ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    videoId: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "competition_id", "videoId", name="uq_competition_item_id_videoId"
        ),
    )


class RatingChoice(Base):
    id: Mapped[uuid_pk]
    rating_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rating.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False
    )
    winner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(CompetitionItem.id, ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    looser_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(CompetitionItem.id, ondelete="CASCADE", onupdate="CASCADE"),
        nullable=True,
    )
    stage: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class Rating(Base):
    id: Mapped[uuid_pk]
    competition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(Competition.id, ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[user_fk]
    ended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    stage: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    choices: Mapped[list[uuid.UUID]] = mapped_column(
        MutableList.as_mutable(ARRAY(UUID)), default=[]
    )
    is_refreshed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_refreshable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ProhibitedTokens(Base):
    id: Mapped[int_pk]
    token: Mapped[str] = mapped_column(String, nullable=False)
    expiration_time: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
