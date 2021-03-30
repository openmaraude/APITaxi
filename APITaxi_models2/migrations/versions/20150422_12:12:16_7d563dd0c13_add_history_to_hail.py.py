"""Add history to hail

Revision ID: 7d563dd0c13
Revises: 3b8033532af1
Create Date: 2015-04-22 12:12:16.658415

"""

# revision identifiers, used by Alembic.
revision = '7d563dd0c13'
down_revision = '3b8033532af1'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
sources_enum = sa.Enum('form', 'api', name='sources')
def upgrade():
    sources_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('customer', sa.Column('added_at', sa.DateTime(), nullable=True))
    op.add_column('customer', sa.Column('added_by', sa.Integer(), nullable=True))
    op.add_column('customer', sa.Column('added_via', sources_enum
        , nullable=True))
    op.add_column('customer', sa.Column('last_update_at', sa.DateTime(), nullable=True))
    op.add_column('customer', sa.Column('source', sa.String(length=255),
        nullable=True))
    op.create_foreign_key(None, 'customer', 'user', ['added_by'], ['id'])
    op.add_column('hail', sa.Column('added_at', sa.DateTime(), nullable=True))
    op.add_column('hail', sa.Column('added_by', sa.Integer(), nullable=True))
    op.add_column('hail', sa.Column('added_via',
        sa.Enum('form', 'api', name='sources'), nullable=True))
    op.add_column('hail', sa.Column('last_update_at', sa.DateTime(), nullable=True))
    op.add_column('hail', sa.Column('source', sa.String(length=255),
        nullable=True))
    op.create_foreign_key(None, 'hail', 'user', ['added_by'], ['id'])
    op.execute("update customer set source = ''")
    op.execute("update customer set added_via = 'api'")
    op.execute("update hail set source = ''")
    op.execute("update hail set added_via = 'api'")
    hail_table = sa.sql.table('hail', sa.sql.column('added_via', 'source'))
    customer_table = sa.sql.table('customer', sa.sql.column('added_via', 'source'))
    op.alter_column('customer', 'added_via', nullable=False)
    op.alter_column('customer', 'source', nullable=False)
    op.alter_column('hail', 'added_via', nullable=False)
    op.alter_column('hail', 'source', nullable=False)


def downgrade():
    op.drop_constraint(None, 'hail', type_='foreignkey')
    op.drop_column('hail', 'source')
    op.drop_column('hail', 'last_update_at')
    op.drop_column('hail', 'added_via')
    op.drop_column('hail', 'added_by')
    op.drop_column('hail', 'added_at')
    op.drop_constraint(None, 'customer', type_='foreignkey')
    op.drop_column('customer', 'source')
    op.drop_column('customer', 'last_update_at')
    op.drop_column('customer', 'added_via')
    op.drop_column('customer', 'added_by')
    op.drop_column('customer', 'added_at')
    sources_enum.drop(op.get_bind(), checkfirst=True)
