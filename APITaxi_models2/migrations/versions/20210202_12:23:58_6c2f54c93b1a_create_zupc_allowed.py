"""Create ZUPC.allowed

Revision ID: 6c2f54c93b1a
Revises: 8cfcc4665458
Create Date: 2021-02-02 12:23:58.755766

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6c2f54c93b1a'
down_revision = '8cfcc4665458'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'town_zupc',
        sa.Column('town_id', sa.Integer(), nullable=True),
        sa.Column('zupc_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['town_id'], ['town.id'], ),
        sa.ForeignKeyConstraint(['zupc_id'], ['ZUPC.id'], )
    )


def downgrade():
    op.drop_table('town_zupc')
