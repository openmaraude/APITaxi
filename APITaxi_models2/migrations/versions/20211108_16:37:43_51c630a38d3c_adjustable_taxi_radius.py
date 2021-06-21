"""Adjustable taxi radius

Revision ID: 51c630a38d3c
Revises: 50f5b6fadda8
Create Date: 2021-11-08 16:37:43.217463

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '51c630a38d3c'
down_revision = '50f5b6fadda8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('vehicle_description', sa.Column('radius', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('vehicle_description', 'radius')
