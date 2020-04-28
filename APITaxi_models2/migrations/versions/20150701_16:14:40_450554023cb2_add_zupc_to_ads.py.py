"""Add zupc to ADS

Revision ID: 450554023cb2
Revises: 2e65dbaa935
Create Date: 2015-07-01 16:14:40.817104

"""

# revision identifiers, used by Alembic.
revision = '450554023cb2'
down_revision = '2e65dbaa935'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('ADS', sa.Column('zupc_id', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('ADS', 'zupc_id')
