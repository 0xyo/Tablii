"""add icon_url to categories

Revision ID: b7c1a2d9e4f6
Revises: f3d4b6a7c9e1
Create Date: 2026-04-22 20:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c1a2d9e4f6'
down_revision = 'f3d4b6a7c9e1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.add_column(sa.Column('icon_url', sa.String(length=300), nullable=True))


def downgrade():
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.drop_column('icon_url')
