"""finalise fake_taxi_id

Revision ID: 87863e7c0dfb
Revises: 910dc6b68dc5
Create Date: 2023-08-07 09:06:47.550877

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '87863e7c0dfb'
down_revision = '910dc6b68dc5'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text('UPDATE hail SET fake_taxi_id = taxi_id WHERE fake_taxi_id IS NULL'))
    op.alter_column('hail', 'fake_taxi_id',
               existing_type=sa.VARCHAR(),
               nullable=False)


def downgrade():
    op.alter_column('hail', 'fake_taxi_id',
               existing_type=sa.VARCHAR(),
               nullable=True)
