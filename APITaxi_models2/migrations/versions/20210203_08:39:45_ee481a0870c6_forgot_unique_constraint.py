"""Forgot unique constraint

Revision ID: ee481a0870c6
Revises: 6c2f54c93b1a
Create Date: 2021-02-03 08:39:45.804523

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'ee481a0870c6'
down_revision = '6c2f54c93b1a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint('unique_pair', 'town_zupc', ['town_id', 'zupc_id'])


def downgrade():
    op.drop_constraint('unique_pair', 'town_zupc', type_='unique')
