"""Status on description

Revision ID: 3ce723f8065a
Revises: 48a67526c4d7
Create Date: 2015-06-01 11:49:32.064622

"""

# revision identifiers, used by Alembic.
revision = '3ce723f8065a'
down_revision = '48a67526c4d7'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

status_enum = postgresql.ENUM('free', 'answering', 'occupied', 'oncoming', 'off', name='status_vehicle_enum')
status_enum_taxi = postgresql.ENUM('free', 'answering', 'occupied', 'oncoming', 'off', name='status_taxi_enum')
def upgrade():
    op.drop_column('taxi', 'status')
    status_enum_taxi.drop(op.get_bind())
    status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('vehicle_description', sa.Column('status', status_enum, default='off'))



def downgrade():
    status_enum_taxi.create(op.get_bind(), checkfirst=True)
    op.add_column('taxi', sa.Column('status', status_enum_taxi, autoincrement=False, nullable=True))
    op.drop_column('vehicle_description', 'status')

