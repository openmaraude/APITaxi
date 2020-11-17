""" Clean up of hail endpoint column in three steps:
- remove unused staging column
- remove now obsolete testing column
- make hail_endpoint_production non null

Revision ID: aa6d3d875f28
Revises: 8bd62cba881a
Create Date: 2020-11-17 09:28:10.910999

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'aa6d3d875f28'
down_revision = '8bd62cba881a'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('user', 'hail_endpoint_staging')
    op.drop_column('user', 'hail_endpoint_testing')
    op.execute('''update "user" set hail_endpoint_production = '' where hail_endpoint_production is null''')
    op.alter_column('user', 'hail_endpoint_production', existing_type=sa.VARCHAR(), server_default='', nullable=False)


def downgrade():
    op.alter_column('user', 'hail_endpoint_production',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.add_column('user', sa.Column('hail_endpoint_testing', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('user', sa.Column('hail_endpoint_staging', sa.VARCHAR(), autoincrement=False, nullable=True))
