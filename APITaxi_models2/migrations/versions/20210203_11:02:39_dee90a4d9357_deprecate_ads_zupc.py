"""Deprecate ADS.zupc

Revision ID: dee90a4d9357
Revises: 49da8bf913fb
Create Date: 2021-02-03 11:02:39.804998

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dee90a4d9357'
down_revision = '49da8bf913fb'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('ADS', 'zupc_id',
                    existing_type=sa.INTEGER(),
                    nullable=True)


def downgrade():
    op.alter_column('ADS', 'zupc_id',
                    existing_type=sa.INTEGER(),
                    nullable=False)
