"""Add internal_id field to taxi

Revision ID: 243adac5e3e9
Revises: bb73d477a1c4
Create Date: 2016-12-01 12:56:08.099162

"""

# revision identifiers, used by Alembic.
revision = '243adac5e3e9'
down_revision = 'bb73d477a1c4'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('vehicle_description', sa.Column('internal_id', sa.String(), nullable=True))


def downgrade():
    op.drop_column('vehicle_description', 'internal_id')
