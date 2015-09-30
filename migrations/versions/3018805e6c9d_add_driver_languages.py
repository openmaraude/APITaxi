"""Add driver languages

Revision ID: 3018805e6c9d
Revises: 14b6c76f933f
Create Date: 2015-09-30 11:34:08.164055

"""

# revision identifiers, used by Alembic.
revision = '3018805e6c9d'
down_revision = '14b6c76f933f'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('driver', sa.Column('languages', postgresql.ARRAY(sa.String()), nullable=True))

def downgrade():
    op.drop_column('driver', 'languages')
