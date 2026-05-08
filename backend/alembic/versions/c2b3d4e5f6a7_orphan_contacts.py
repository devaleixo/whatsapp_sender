"""orphan contacts: campaign_id nullable

Revision ID: c2b3d4e5f6a7
Revises: b1a2c3d4e5f6
Create Date: 2026-04-25 12:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c2b3d4e5f6a7'
down_revision: Union[str, None] = 'b1a2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.alter_column('campaign_id', existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.alter_column('campaign_id', existing_type=sa.Integer(), nullable=False)
