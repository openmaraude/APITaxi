"""pmr tag on vehicle description

Revision ID: ed669e53e432
Revises: 7e794be3bf55
Create Date: 2023-02-08 10:38:28.017169

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ed669e53e432'
down_revision = '7e794be3bf55'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('vehicle_description', sa.Column('pmr', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('vehicle_description', 'pmr')
