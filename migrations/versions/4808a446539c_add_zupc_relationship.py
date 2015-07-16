"""Add zupc relationship

Revision ID: 4808a446539c
Revises: 450554023cb2
Create Date: 2015-07-16 16:36:30.441812

"""

# revision identifiers, used by Alembic.
revision = '4808a446539c'
down_revision = '450554023cb2'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
name = 'fkey_zupc_ads'
def upgrade():
    op.create_foreign_key(name, 'ADS', 'ZUPC', ['zupc_id'], ['id'])


def downgrade():
    op.drop_constraint(name, 'ADS', type_='foreignkey')
