"""Add max distance to ZUPC

Revision ID: 986de51c9c9f
Revises: 3e54873a977a
Create Date: 2016-10-05 11:07:13.831909

"""

# revision identifiers, used by Alembic.
revision = '986de51c9c9f'
down_revision = '3e54873a977a'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('ZUPC', sa.Column('max_distance', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('ZUPC', 'max_distance')
