"""Add reason/rating on taxi and customer

Revision ID: 463ab467b156
Revises: 53c6b52778a7
Create Date: 2015-07-17 11:07:20.760652

"""

# revision identifiers, used by Alembic.
revision = '463ab467b156'
down_revision = '53c6b52778a7'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
rating_ride_reason_enum = sa.Enum('late', 'no_credit_card', 'bad_itinerary',
                                'dirty_taxi', name='rating_ride_reason_enum')
reporting_customer_reason_enum = sa.Enum('late', 'aggressive', 'no_show',
                                name='reporting_customer_reason_enum')
incident_customer_reason_enum = sa.Enum('mud_river', 'parade', 'earthquake',
        name='incident_customer_reason_enum')
incident_taxi_reason_enum = sa.Enum('traffic_jam', 'garbage_truck',
        name='incident_taxi_reason_enum')

def upgrade():
    reporting_customer_reason_enum.create(op.get_bind())
    rating_ride_reason_enum.create(op.get_bind())
    incident_customer_reason_enum.create(op.get_bind())
    incident_taxi_reason_enum.create(op.get_bind())
    op.add_column('hail', sa.Column('reporting_customer', sa.Boolean(),
        nullable=True))
    op.add_column('hail', sa.Column('reporting_customer_reason',
        reporting_customer_reason_enum, nullable=True))
    op.add_column('hail', sa.Column('incident_customer_reason',
        incident_customer_reason_enum, nullable=True))
    op.add_column('hail', sa.Column('incident_taxi_reason',
        incident_taxi_reason_enum, nullable=True))
    op.add_column('hail', sa.Column('rating_ride_reason',
        rating_ride_reason_enum, nullable=True))
    op.add_column('hail', sa.Column('rating_ride',
        sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('hail', 'rating_ride')
    op.drop_column('hail', 'rating_ride_reason')
    op.drop_column('hail', 'incident_customer_reason')
    op.drop_column('hail', 'incident_taxi_reason')
    op.drop_column('hail', 'reporting_customer_reason')
    op.drop_column('hail', 'reporting_customer')
    rating_ride_reason_enum.drop(op.get_bind())
    reporting_customer_reason_enum.drop(op.get_bind())
    incident_customer_reason_enum.drop(op.get_bind())
    incident_taxi_reason_enum.drop(op.get_bind())
