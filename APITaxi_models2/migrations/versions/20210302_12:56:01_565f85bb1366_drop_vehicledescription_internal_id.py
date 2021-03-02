"""drop VehicleDescription.internal_id

Revision ID: 565f85bb1366
Revises: 54e7b2b8da6d
Create Date: 2021-03-02 12:56:01.739704

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '565f85bb1366'
down_revision = '54e7b2b8da6d'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('vehicle_description', 'internal_id')


def downgrade():
    op.add_column('vehicle_description', sa.Column('internal_id', sa.VARCHAR(), autoincrement=False, nullable=True))
