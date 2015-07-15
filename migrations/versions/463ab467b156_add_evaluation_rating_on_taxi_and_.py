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
reason_customer_enum = sa.Enum('late', 'aggressive', 'no_show', name='reason_incident_customer_enum')
reason_ride_enum = sa.Enum('late', 'no_credit_card', 'bad_itinerary', 'dirty_taxi', name='reason_rating_ride_enum')

def upgrade():
    reason_customer_enum.create(op.get_bind())
    reason_ride_enum.create(op.get_bind())
    op.add_column('hail', sa.Column('incident_customer_reason', reason_customer_enum, nullable=True))
    op.add_column('hail', sa.Column('rating_ride_reason', reason_ride_enum, nullable=True))
    op.add_column('hail', sa.Column('rating_ride', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('hail', 'rating_ride')
    op.drop_column('hail', 'incident_customer_reason')
    op.drop_column('hail', 'rating_ride_reason')
    reason_customer_enum.drop(op.get_bind())
    reason_taxi_enum.drop(op.get_bind())
