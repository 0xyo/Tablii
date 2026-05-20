"""add payment_completed to subscriptions

Revision ID: c8d9e1f2a3b4
Revises: b7c1a2d9e4f6
Create Date: 2026-05-19 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c8d9e1f2a3b4'
down_revision = 'b7c1a2d9e4f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('payment_completed', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.drop_column('payment_completed')
