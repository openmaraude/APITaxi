"""Switch session_id to UUID

Revision ID: 6a895756a36b
Revises: aa6d3d875f28
Create Date: 2020-11-25 10:16:10.229018

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '6a895756a36b'
down_revision = 'aa6d3d875f28'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text('create extension if not exists "uuid-ossp"'))
    # First just make the column nullable
    op.alter_column('hail', 'session_id',
                    existing_type=sa.VARCHAR(),
                    nullable=True,
                    existing_server_default=sa.text("''::character varying"),
                    server_default=None)
    op.execute(sa.text('update hail set session_id = null'))
    # Now we can convert from varchar to uuid
    op.alter_column('hail', 'session_id',
                    type_=postgresql.UUID(),
                    postgresql_using='session_id::uuid',
                    nullable=True,
                    server_default=func.uuid_generate_v4())
    # After a script has filled up the old session IDs, and the API the new ones,
    # make the column not nullable


def downgrade():
    op.alter_column('hail', 'session_id',
                    existing_type=postgresql.UUID(),
                    type_=sa.VARCHAR(),
                    nullable=True,
                    existing_server_default=func.uuid_generate_v4(),
                    server_default=sa.text("''::character varying"))
