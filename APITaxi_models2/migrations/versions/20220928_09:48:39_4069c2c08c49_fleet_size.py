"""Fleet size

Revision ID: 4069c2c08c49
Revises: 5001a09d73d3
Create Date: 2022-09-28 09:48:39.247686

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4069c2c08c49'
down_revision = 'b7987048ab8e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('fleet_size', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('user', 'fleet_size')
