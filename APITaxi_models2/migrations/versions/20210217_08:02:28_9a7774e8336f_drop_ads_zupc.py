"""drop ADS.zupc

Revision ID: 9a7774e8336f
Revises: 4f1ef685ca46
Create Date: 2021-02-17 08:02:28.565099

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9a7774e8336f'
down_revision = '4f1ef685ca46'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('fkey_zupc_ads', 'ADS', type_='foreignkey')
    op.drop_column('ADS', 'zupc_id')


def downgrade():
    op.add_column('ADS', sa.Column('zupc_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('fkey_zupc_ads', 'ADS', 'ZUPC', ['zupc_id'], ['id'])
