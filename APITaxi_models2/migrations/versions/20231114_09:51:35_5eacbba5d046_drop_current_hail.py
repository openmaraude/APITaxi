"""Drop current_hail

Revision ID: 5eacbba5d046
Revises: 87863e7c0dfb
Create Date: 2023-11-14 09:51:35.726326

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '5eacbba5d046'
down_revision = '87863e7c0dfb'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('taxi_hail_id', 'taxi', type_='foreignkey')
    op.drop_column('taxi', 'current_hail_id')


def downgrade():
    op.add_column('taxi', sa.Column('current_hail_id', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.create_foreign_key('taxi_hail_id', 'taxi', 'hail', ['current_hail_id'], ['id'], deferrable=True)
