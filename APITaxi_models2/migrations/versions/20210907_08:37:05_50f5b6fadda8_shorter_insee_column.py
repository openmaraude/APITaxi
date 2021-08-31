"""Shorter INSEE column

Revision ID: 50f5b6fadda8
Revises: 5b8d8ca36aeb
Create Date: 2021-09-07 08:37:05.248880

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '50f5b6fadda8'
down_revision = '5b8d8ca36aeb'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('town', 'insee', existing_type=sa.VARCHAR(), type_=sa.VARCHAR(5))


def downgrade():
    op.alter_column('town', 'insee', existing_type=sa.VARCHAR(5), type_=sa.VARCHAR())
