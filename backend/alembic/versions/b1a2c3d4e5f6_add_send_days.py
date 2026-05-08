"""add send_days

Revision ID: b1a2c3d4e5f6
Revises: af400061e73e
Create Date: 2026-04-25 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1a2c3d4e5f6'
down_revision: Union[str, None] = 'af400061e73e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('app_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('send_days', sa.String(length=32), nullable=False, server_default='0,1,2,3,4'))


def downgrade() -> None:
    with op.batch_alter_table('app_settings', schema=None) as batch_op:
        batch_op.drop_column('send_days')
