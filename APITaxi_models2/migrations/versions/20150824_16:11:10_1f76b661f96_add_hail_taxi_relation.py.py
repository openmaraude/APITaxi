"""Add hail taxi relation

Revision ID: 1f76b661f96
Revises: 463ab467b156
Create Date: 2015-08-24 16:11:10.590330

"""

# revision identifiers, used by Alembic.
revision = '1f76b661f96'
down_revision = '463ab467b156'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_foreign_key('hail_taxi_relation', 'hail', 'taxi', ['taxi_id'], ['id'])


def downgrade():
    op.drop_constraint('hail_taxi_relation', 'hail', type_='foreignkey')
