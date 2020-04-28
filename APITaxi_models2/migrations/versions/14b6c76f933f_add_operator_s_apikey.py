"""Add operator's apikey

Revision ID: 14b6c76f933f
Revises: 1b2ea289bd1
Create Date: 2015-09-15 12:28:36.363332

"""

# revision identifiers, used by Alembic.
revision = '14b6c76f933f'
down_revision = '1b2ea289bd1'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('user', sa.Column('operator_api_key', sa.String(), nullable=True))
    op.add_column('user', sa.Column('operator_header_name', sa.String(), nullable=True))


def downgrade():
    op.drop_column('user', 'operator_header_name')
    op.drop_column('user', 'operator_api_key')
