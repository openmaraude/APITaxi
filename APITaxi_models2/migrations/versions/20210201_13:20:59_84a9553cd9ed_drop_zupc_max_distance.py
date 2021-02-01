"""Drop ZUPC.max_distance

Revision ID: 84a9553cd9ed
Revises: 8917b96b3b4d
Create Date: 2021-02-01 13:20:59.308236

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '84a9553cd9ed'
down_revision = '8917b96b3b4d'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('ZUPC', 'max_distance')


def downgrade():
    op.add_column('ZUPC', sa.Column('max_distance', sa.INTEGER(), autoincrement=False, nullable=True))
