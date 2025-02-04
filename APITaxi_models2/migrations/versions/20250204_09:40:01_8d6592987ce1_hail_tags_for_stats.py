"""hail tags for stats

Revision ID: 8d6592987ce1
Revises: 84b3ccf6a8fa
Create Date: 2025-02-04 09:40:01.473661

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8d6592987ce1'
down_revision = '84b3ccf6a8fa'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('stats_hails', sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade():
    op.drop_column('stats_hails', 'tags')
