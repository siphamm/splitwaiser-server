"""initial schema

Revision ID: 0f79bcd1dcec
Revises:
Create Date: 2026-02-11 23:59:08.377769

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f79bcd1dcec'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'trips',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('access_token', sa.String(24), unique=True, nullable=False, index=True),
        sa.Column('creator_token', sa.String(48), nullable=False),
        sa.Column('creator_member_id', sa.String(), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('settlement_currency', sa.String(3), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    op.create_table(
        'members',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('trip_id', sa.String(), sa.ForeignKey('trips.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('settled_by_id', sa.String(), sa.ForeignKey('members.id', ondelete='SET NULL'), nullable=True),
        sa.Column('settlement_currency', sa.String(3), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # Add FK from trips.creator_member_id -> members.id (use_alter due to circular ref)
    op.create_foreign_key(
        'trips_creator_member_id_fkey', 'trips', 'members',
        ['creator_member_id'], ['id'],
    )

    op.create_table(
        'expenses',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('trip_id', sa.String(), sa.ForeignKey('trips.id', ondelete='CASCADE'), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('paid_by_id', sa.String(), sa.ForeignKey('members.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('split_method', sa.String(20), nullable=False),
        sa.Column('currency', sa.String(3), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    op.create_table(
        'expense_members',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('expense_id', sa.String(), sa.ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('member_id', sa.String(), sa.ForeignKey('members.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('split_value', sa.Numeric(), nullable=True),
        sa.UniqueConstraint('expense_id', 'member_id'),
    )

    op.create_table(
        'settlements',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('trip_id', sa.String(), sa.ForeignKey('trips.id', ondelete='CASCADE'), nullable=False),
        sa.Column('from_member_id', sa.String(), sa.ForeignKey('members.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('to_member_id', sa.String(), sa.ForeignKey('members.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    op.create_table(
        'exchange_rates',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('base_currency', sa.String(3), nullable=False),
        sa.Column('target_currency', sa.String(3), nullable=False),
        sa.Column('rate', sa.Numeric(18, 8), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('date', 'base_currency', 'target_currency'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('exchange_rates')
    op.drop_table('settlements')
    op.drop_table('expense_members')
    op.drop_table('expenses')
    op.drop_constraint('trips_creator_member_id_fkey', 'trips', type_='foreignkey')
    op.drop_table('members')
    op.drop_table('trips')
