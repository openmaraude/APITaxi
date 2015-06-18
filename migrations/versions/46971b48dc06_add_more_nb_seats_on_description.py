"""Add more nb_seats on description

Revision ID: 46971b48dc06
Revises: 18da28fb974c
Create Date: 2015-06-18 11:32:39.817244

"""

# revision identifiers, used by Alembic.
revision = '46971b48dc06'
down_revision = '18da28fb974c'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('vehicle_description', sa.Column('nb_seats', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('vehicle_description', 'nb_seats')
