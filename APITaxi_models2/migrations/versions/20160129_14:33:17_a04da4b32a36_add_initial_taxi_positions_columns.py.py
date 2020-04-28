"""Add initial_taxi positions columns

Revision ID: a04da4b32a36
Revises: 30bcf72d7430
Create Date: 2016-01-29 14:33:17.695352

"""

# revision identifiers, used by Alembic.
revision = 'a04da4b32a36'
down_revision = '30bcf72d7430'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('hail', sa.Column('initial_taxi_lat', sa.Float(), nullable=True))
    op.add_column('hail', sa.Column('initial_taxi_lon', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('hail', 'initial_taxi_lon')
    op.drop_column('hail', 'initial_taxi_lat')
