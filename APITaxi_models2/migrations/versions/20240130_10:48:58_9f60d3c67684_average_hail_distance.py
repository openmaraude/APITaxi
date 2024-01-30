"""average hail distance

Revision ID: 9f60d3c67684
Revises: 5eacbba5d046
Create Date: 2024-01-30 10:48:58.097105

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9f60d3c67684'
down_revision = '5eacbba5d046'
branch_labels = None
depends_on = None


def upgrade():
    """
    To fill:
    update stats_hails s set hail_distance=(select st_distance(st_point(customer_lon, customer_lat)::geography, st_point(initial_taxi_lon, initial_taxi_lat)::geography) from hail h where s.id=h.id and blurred=false);
    """
    op.add_column('stats_hails', sa.Column('hail_distance', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('stats_hails', 'hail_distance')
