"""Create ZUPC.zupc_id

Revision ID: 8cfcc4665458
Revises: 918717b2e507
Create Date: 2021-02-02 10:45:01.412883

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8cfcc4665458'
down_revision = '918717b2e507'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ZUPC', sa.Column('zupc_id', postgresql.UUID(), nullable=True))


def downgrade():
    op.drop_column('ZUPC', 'zupc_id')
