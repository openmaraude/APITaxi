"""add hail transition log

Revision ID: 34a39e9fb39a
Revises: 81bab94157fc
Create Date: 2021-03-01 13:22:47.445231

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '34a39e9fb39a'
down_revision = '81bab94157fc'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('hail', sa.Column('transition_log', postgresql.JSON(astext_type=sa.Text()), server_default='[]', nullable=False))


def downgrade():
    op.drop_column('hail', 'transition_log')
