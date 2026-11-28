"""grant backend api role

Revision ID: 7d85d8f90680
Revises: 68dadf785e18
Create Date: 2026-11-28 16:16:13.720834

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d85d8f90680'
down_revision: Union[str, Sequence[str], None] = '68dadf785e18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    if op.get_bind().dialect.name == "postgresql":
        op.execute("GRANT myhr_api TO postgres")


def downgrade() -> None:
    """Downgrade schema."""
    if op.get_bind().dialect.name == "postgresql":
        op.execute("REVOKE myhr_api FROM postgres")
