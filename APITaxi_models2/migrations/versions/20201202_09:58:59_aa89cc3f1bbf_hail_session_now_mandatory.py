"""hail session now mandatory

Revision ID: aa89cc3f1bbf
Revises: 6a895756a36b
Create Date: 2020-12-02 09:58:59.630918

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'aa89cc3f1bbf'
down_revision = '6a895756a36b'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('hail', 'session_id',
               existing_type=postgresql.UUID(),
               nullable=False,
               existing_server_default=sa.text('uuid_generate_v4()'))


def downgrade():
    op.alter_column('hail', 'session_id',
               existing_type=postgresql.UUID(),
               nullable=True,
               existing_server_default=sa.text('uuid_generate_v4()'))
