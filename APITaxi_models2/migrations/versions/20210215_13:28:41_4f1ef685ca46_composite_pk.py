"""composite PK

Revision ID: 4f1ef685ca46
Revises: dee90a4d9357
Create Date: 2021-02-15 13:28:41.490733

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '4f1ef685ca46'
down_revision = 'dee90a4d9357'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('unique_pair', 'town_zupc', type_='unique')
    op.create_primary_key('town_zupc_pk', 'town_zupc', ['town_id', 'zupc_id'])


def downgrade():
    op.drop_primary_key('town_zupc_pk', table_name='town_zupc')
    op.create_unique_constraint('unique_pair', 'town_zupc', ['town_id', 'zupc_id'])
