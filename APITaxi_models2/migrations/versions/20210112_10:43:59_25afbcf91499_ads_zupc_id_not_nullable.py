"""ADS.zupc_id not nullable

Revision ID: 25afbcf91499
Revises: ac18f0f134d8
Create Date: 2021-01-12 10:43:59.317874

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '25afbcf91499'
down_revision = 'ac18f0f134d8'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'ADS', 'zupc_id',
        existing_type=sa.INTEGER(),
        nullable=False
    )


def downgrade():
    op.alter_column(
        'ADS', 'zupc_id',
        existing_type=sa.INTEGER(),
        nullable=True
    )
