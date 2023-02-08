"""station.added_at update

Revision ID: 861188cd0769
Revises: ed669e53e432
Create Date: 2023-02-08 13:32:21.599609

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '861188cd0769'
down_revision = 'ed669e53e432'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('station', 'added_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)


def downgrade():
    op.alter_column('station', 'added_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
