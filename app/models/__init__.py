import uuid
from sqlalchemy.orm import mapped_column
from datetime import datetime
from sqlalchemy import func
from typing import Annotated
from sqlalchemy.dialects.postgresql import UUID


int_pk = Annotated[int, mapped_column(primary_key=True)]
uuid_pk = Annotated[
    uuid.UUID, mapped_column(UUID, nullable=False, primary_key=True, default=uuid.uuid4)
]
created_at = Annotated[datetime, mapped_column(server_default=func.now())]
updated_at = Annotated[
    datetime, mapped_column(server_default=func.now(), onupdate=datetime.now)
]
str_uniq = Annotated[str, mapped_column(unique=True, nullable=False)]
str_nullable = Annotated[str, mapped_column(nullable=True)]
