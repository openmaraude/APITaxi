"""fake_taxi_id

Revision ID: 910dc6b68dc5
Revises: 2c8f739eae00
Create Date: 2023-07-25 13:06:16.662748

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '910dc6b68dc5'
down_revision = '2c8f739eae00'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('hail', sa.Column('fake_taxi_id', sa.String(), nullable=True))


def downgrade():
    op.drop_column('hail', 'fake_taxi_id')
