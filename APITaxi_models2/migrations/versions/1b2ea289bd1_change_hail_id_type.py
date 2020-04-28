"""Change hail id type

Revision ID: 1b2ea289bd1
Revises: 1f76b661f96
Create Date: 2015-09-14 16:28:35.234009

"""

# revision identifiers, used by Alembic.
revision = '1b2ea289bd1'
down_revision = '1f76b661f96'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.alter_column('hail', 'id', existing_type=sa.Integer, type_=sa.String)

def downgrade():
    op.alter_column('hail', 'id', type=sa.Integer, existing_type=sa.String)

