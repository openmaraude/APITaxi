"""Make ADS.owner_type NULLABLE

Revision ID: 8bd62cba881a
Revises: bed87a19db76
Create Date: 2020-11-10 10:37:31.273549

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8bd62cba881a'
down_revision = 'bed87a19db76'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('ADS', 'owner_type', existing_type=postgresql.ENUM('company', 'individual', name='owner_type_enum'), nullable=True)


def downgrade():
    op.alter_column('ADS', 'owner_type', existing_type=postgresql.ENUM('company', 'individual', name='owner_type_enum'), nullable=False)
