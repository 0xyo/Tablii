"""add ramadan_iftar_time to restaurants

Revision ID: f3d4b6a7c9e1
Revises: 769dd292416d
Create Date: 2026-04-12 19:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3d4b6a7c9e1'
down_revision = '769dd292416d'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('restaurants')}
    if 'ramadan_iftar_time' not in columns:
        with op.batch_alter_table('restaurants', schema=None) as batch_op:
            batch_op.add_column(sa.Column('ramadan_iftar_time', sa.Time(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('restaurants')}
    if 'ramadan_iftar_time' in columns:
        with op.batch_alter_table('restaurants', schema=None) as batch_op:
            batch_op.drop_column('ramadan_iftar_time')
