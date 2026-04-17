"""add avatar_url to users and staff_users

Revision ID: a6b3f1c2d4e5
Revises: f3d4b6a7c9e1
Create Date: 2026-04-17 12:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a6b3f1c2d4e5'
down_revision = 'f3d4b6a7c9e1'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {col['name'] for col in inspector.get_columns('users')}
    if 'avatar_url' not in user_columns:
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.add_column(sa.Column('avatar_url', sa.String(length=300), nullable=True))

    staff_columns = {col['name'] for col in inspector.get_columns('staff_users')}
    if 'avatar_url' not in staff_columns:
        with op.batch_alter_table('staff_users', schema=None) as batch_op:
            batch_op.add_column(sa.Column('avatar_url', sa.String(length=300), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {col['name'] for col in inspector.get_columns('users')}
    if 'avatar_url' in user_columns:
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.drop_column('avatar_url')

    staff_columns = {col['name'] for col in inspector.get_columns('staff_users')}
    if 'avatar_url' in staff_columns:
        with op.batch_alter_table('staff_users', schema=None) as batch_op:
            batch_op.drop_column('avatar_url')
