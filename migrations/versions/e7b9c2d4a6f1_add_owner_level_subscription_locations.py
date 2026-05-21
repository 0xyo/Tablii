"""add owner-level subscription locations

Revision ID: e7b9c2d4a6f1
Revises: c8d9e1f2a3b4
Create Date: 2026-05-21 18:30:00.000000
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7b9c2d4a6f1'
down_revision = 'c8d9e1f2a3b4'
branch_labels = None
depends_on = None


PLAN_LIMITS = {
    'free': {'max_locations': 1, 'max_tables': 5, 'max_items': 20},
    'pro': {'max_locations': 3, 'max_tables': 25, 'max_items': 100},
    'enterprise': {'max_locations': 999, 'max_tables': 999, 'max_items': 999},
}


def _columns(table_name):
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col['name'] for col in inspector.get_columns(table_name)}


def _indexes(table_name):
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {idx['name'] for idx in inspector.get_indexes(table_name)}


def upgrade():
    columns = _columns('subscriptions')
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        if 'owner_id' not in columns:
            batch_op.add_column(sa.Column('owner_id', sa.Integer(), nullable=True))
        if 'max_locations' not in columns:
            batch_op.add_column(sa.Column('max_locations', sa.Integer(), nullable=True))

    bind = op.get_bind()

    bind.execute(sa.text(
        """
        UPDATE subscriptions
        SET owner_id = (
            SELECT restaurants.owner_id
            FROM restaurants
            WHERE restaurants.id = subscriptions.restaurant_id
        )
        WHERE owner_id IS NULL
          AND restaurant_id IS NOT NULL
        """
    ))

    for plan, limits in PLAN_LIMITS.items():
        bind.execute(
            sa.text(
                """
                UPDATE subscriptions
                SET max_locations = :max_locations,
                    max_tables = COALESCE(max_tables, :max_tables),
                    max_items = COALESCE(max_items, :max_items)
                WHERE plan = :plan
                  AND (max_locations IS NULL OR max_locations < 1)
                """
            ),
            {
                'plan': plan,
                'max_locations': limits['max_locations'],
                'max_tables': limits['max_tables'],
                'max_items': limits['max_items'],
            },
        )

    bind.execute(sa.text(
        """
        UPDATE subscriptions
        SET max_locations = 1
        WHERE max_locations IS NULL OR max_locations < 1
        """
    ))

    owners = bind.execute(sa.text(
        """
        SELECT users.id AS owner_id, MIN(restaurants.id) AS restaurant_id
        FROM users
        JOIN restaurants ON restaurants.owner_id = users.id
        WHERE users.role = 'owner'
        GROUP BY users.id
        """
    )).mappings().all()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for owner in owners:
        existing = bind.execute(
            sa.text(
                """
                SELECT id
                FROM subscriptions
                WHERE owner_id = :owner_id
                LIMIT 1
                """
            ),
            {'owner_id': owner['owner_id']},
        ).first()
        if existing:
            continue

        bind.execute(
            sa.text(
                """
                INSERT INTO subscriptions (
                    owner_id, restaurant_id, plan, max_locations, max_tables,
                    max_items, started_at, is_active, payment_completed
                )
                VALUES (
                    :owner_id, :restaurant_id, 'free', 1, 5,
                    20, :started_at, :is_active, :payment_completed
                )
                """
            ),
            {
                'owner_id': owner['owner_id'],
                'restaurant_id': owner['restaurant_id'],
                'started_at': now,
                'is_active': True,
                'payment_completed': False,
            },
        )

    duplicates = bind.execute(sa.text(
        """
        SELECT owner_id, MIN(id) AS keep_id
        FROM subscriptions
        WHERE owner_id IS NOT NULL
        GROUP BY owner_id
        HAVING COUNT(*) > 1
        """
    )).mappings().all()

    for duplicate in duplicates:
        bind.execute(
            sa.text(
                """
                UPDATE subscriptions
                SET owner_id = NULL
                WHERE owner_id = :owner_id
                  AND id != :keep_id
                """
            ),
            {
                'owner_id': duplicate['owner_id'],
                'keep_id': duplicate['keep_id'],
            },
        )

    if 'ix_subscriptions_owner_id' not in _indexes('subscriptions'):
        op.create_index(
            'ix_subscriptions_owner_id',
            'subscriptions',
            ['owner_id'],
            unique=True,
        )


def downgrade():
    if 'ix_subscriptions_owner_id' in _indexes('subscriptions'):
        op.drop_index('ix_subscriptions_owner_id', table_name='subscriptions')

    columns = _columns('subscriptions')
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        if 'max_locations' in columns:
            batch_op.drop_column('max_locations')
        if 'owner_id' in columns:
            batch_op.drop_column('owner_id')
