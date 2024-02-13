"""VASP handicap

Revision ID: e8ca55149b91
Revises: 9f60d3c67684
Create Date: 2024-02-13 10:41:35.129578

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e8ca55149b91'
down_revision = '9f60d3c67684'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('vehicle_description', sa.Column('vasp_handicap', sa.Boolean(), nullable=True))
    op.drop_column('vehicle_description', 'pmr')


def downgrade():
    op.add_column('vehicle_description', sa.Column('pmr', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.drop_column('vehicle_description', 'vasp_handicap')
