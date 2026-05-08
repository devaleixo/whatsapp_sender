"""remarketing: parent_campaign_id and per-row campaign_id

Revision ID: d3e4f5a6b7c8
Revises: c2b3d4e5f6a7
Create Date: 2026-04-26 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, None] = 'c2b3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('campaigns', schema=None) as batch_op:
        batch_op.add_column(sa.Column('parent_campaign_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('remarketing_delay_hours', sa.Integer(), nullable=False, server_default='48'))
        batch_op.add_column(sa.Column('exclude_replied', sa.Boolean(), nullable=False, server_default=sa.text('1')))
        batch_op.add_column(sa.Column('exclude_replied_scope', sa.String(length=16), nullable=False, server_default='phone'))
        batch_op.add_column(sa.Column('max_followups', sa.Integer(), nullable=False, server_default='1'))
        batch_op.create_index('ix_campaigns_parent_campaign_id', ['parent_campaign_id'])
        batch_op.create_foreign_key(
            'fk_campaigns_parent_campaign_id', 'campaigns', ['parent_campaign_id'], ['id'], ondelete='SET NULL'
        )

    with op.batch_alter_table('send_queue', schema=None) as batch_op:
        batch_op.add_column(sa.Column('campaign_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_send_queue_campaign_id', ['campaign_id'])
        batch_op.create_foreign_key(
            'fk_send_queue_campaign_id', 'campaigns', ['campaign_id'], ['id'], ondelete='CASCADE'
        )

    with op.batch_alter_table('sends', schema=None) as batch_op:
        batch_op.add_column(sa.Column('campaign_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_sends_campaign_id', ['campaign_id'])
        batch_op.create_foreign_key(
            'fk_sends_campaign_id', 'campaigns', ['campaign_id'], ['id'], ondelete='SET NULL'
        )

    # Back-fill: assign each row's campaign_id from its contact's campaign_id.
    # Only correct for non-remarketing rows (the only kind that exists pre-migration).
    op.execute(
        "UPDATE send_queue SET campaign_id = ("
        "  SELECT campaign_id FROM contacts WHERE contacts.id = send_queue.contact_id"
        ") WHERE campaign_id IS NULL"
    )
    op.execute(
        "UPDATE sends SET campaign_id = ("
        "  SELECT campaign_id FROM contacts WHERE contacts.id = sends.contact_id"
        ") WHERE campaign_id IS NULL"
    )


def downgrade() -> None:
    with op.batch_alter_table('sends', schema=None) as batch_op:
        batch_op.drop_constraint('fk_sends_campaign_id', type_='foreignkey')
        batch_op.drop_index('ix_sends_campaign_id')
        batch_op.drop_column('campaign_id')

    with op.batch_alter_table('send_queue', schema=None) as batch_op:
        batch_op.drop_constraint('fk_send_queue_campaign_id', type_='foreignkey')
        batch_op.drop_index('ix_send_queue_campaign_id')
        batch_op.drop_column('campaign_id')

    with op.batch_alter_table('campaigns', schema=None) as batch_op:
        batch_op.drop_constraint('fk_campaigns_parent_campaign_id', type_='foreignkey')
        batch_op.drop_index('ix_campaigns_parent_campaign_id')
        batch_op.drop_column('max_followups')
        batch_op.drop_column('exclude_replied_scope')
        batch_op.drop_column('exclude_replied')
        batch_op.drop_column('remarketing_delay_hours')
        batch_op.drop_column('parent_campaign_id')
