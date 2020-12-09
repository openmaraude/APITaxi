"""Create manager user

Revision ID: 1980911fa00e
Revises: c536071ddf56
Create Date: 2020-12-09 11:27:42.206439

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1980911fa00e'
down_revision = 'c536071ddf56'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('manager_id', sa.Integer(), nullable=True))
    op.create_foreign_key('user_manager_id_fkey', 'user', 'user', ['manager_id'], ['id'])


def downgrade():
    op.drop_constraint('user_manager_id_fkey', 'user', type_='foreignkey')
    op.drop_column('user', 'manager_id')
