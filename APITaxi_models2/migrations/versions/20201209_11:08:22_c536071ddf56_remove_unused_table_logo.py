"""Remove unused table logo

Revision ID: c536071ddf56
Revises: aa89cc3f1bbf
Create Date: 2020-12-09 11:08:22.901812

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c536071ddf56'
down_revision = 'aa89cc3f1bbf'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('logo')


def downgrade():
    op.create_table('logo',
        sa.Column('id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column('size', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('format_', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], name='logo_user_id_fkey'),
        sa.PrimaryKeyConstraint('id', name='logo_pkey')
    )
