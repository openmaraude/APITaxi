"""Add taxi phone number on hail

Revision ID: 4190b0aefe23
Revises: 46971b48dc06
Create Date: 2015-06-22 19:12:57.417551

"""

# revision identifiers, used by Alembic.
revision = '4190b0aefe23'
down_revision = '46971b48dc06'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('hail', sa.Column('taxi_phone_number', sa.String(), nullable=True))


def downgrade():
    op.drop_column('hail', 'taxi_phone_number')
