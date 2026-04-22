"""add icon_url to categories

Revision ID: b7c1a2d9e4f6
Revises: a6b3f1c2d4e5
Create Date: 2026-04-22 20:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c1a2d9e4f6'
down_revision = 'a6b3f1c2d4e5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.add_column(sa.Column('icon_url', sa.String(length=300), nullable=True))


def downgrade():
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.drop_column('icon_url')
