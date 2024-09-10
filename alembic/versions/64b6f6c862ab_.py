"""empty message

Revision ID: 64b6f6c862ab
Revises: 95ed7b2fc0a0
Create Date: 2024-08-15 22:20:50.927557

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '64b6f6c862ab'
down_revision: Union[str, None] = '95ed7b2fc0a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('prohibited_tokens', 'expiration_time',
               existing_type=postgresql.TIMESTAMP(),
               type_=postgresql.TIMESTAMP(timezone=True),
               existing_nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('prohibited_tokens', 'expiration_time',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)
    # ### end Alembic commands ###
