"""add places columns to contacts

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-05-08

"""
from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, None] = 'd3e4f5a6b7c8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('contacts', sa.Column('neighborhood', sa.String(128), nullable=True))
    op.add_column('contacts', sa.Column('rating_count', sa.String(32), nullable=True))
    op.add_column('contacts', sa.Column('business_type', sa.String(128), nullable=True))
    op.add_column('contacts', sa.Column('business_status', sa.String(32), nullable=True))
    op.add_column('contacts', sa.Column('place_id', sa.String(256), nullable=True))
    op.create_index('ix_contacts_place_id', 'contacts', ['place_id'])


def downgrade() -> None:
    op.drop_index('ix_contacts_place_id', table_name='contacts')
    op.drop_column('contacts', 'place_id')
    op.drop_column('contacts', 'business_status')
    op.drop_column('contacts', 'business_type')
    op.drop_column('contacts', 'rating_count')
    op.drop_column('contacts', 'neighborhood')
