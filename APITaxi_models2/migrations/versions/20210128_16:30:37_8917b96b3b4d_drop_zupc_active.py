"""Drop ZUPC.active

Revision ID: 8917b96b3b4d
Revises: 25afbcf91499
Create Date: 2021-01-28 16:30:37.275187

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8917b96b3b4d'
down_revision = '25afbcf91499'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('ZUPC', 'active')


def downgrade():
    op.add_column('ZUPC', sa.Column('active', sa.BOOLEAN(), autoincrement=False, nullable=True))
