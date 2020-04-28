"""Add hail_endpoint to user

Revision ID: 26311efc301f
Revises: 1b4950ac4433
Create Date: 2015-04-25 17:59:11.255678

"""

# revision identifiers, used by Alembic.
revision = '26311efc301f'
down_revision = '1b4950ac4433'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('user', sa.Column('hail_endpoint', sa.String(), nullable=True))


def downgrade():
    op.drop_column('user', 'hail_endpoint')
