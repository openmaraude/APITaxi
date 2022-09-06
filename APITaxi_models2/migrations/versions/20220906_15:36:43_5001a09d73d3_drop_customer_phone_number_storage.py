"""drop customer phone number storage

Revision ID: 5001a09d73d3
Revises: b459cc4d5d79
Create Date: 2022-09-06 15:36:43.746299

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '5001a09d73d3'
down_revision = 'b459cc4d5d79'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('customer', 'phone_number')


def downgrade():
    op.add_column('customer', sa.Column('phone_number', sa.VARCHAR(), autoincrement=False, nullable=True))
