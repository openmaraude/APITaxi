"""Add moteur to roles

Revision ID: 4e62a5e5f592
Revises: 42e1b5e7b295
Create Date: 2015-05-27 16:08:49.275230

"""

# revision identifiers, used by Alembic.
revision = '4e62a5e5f592'
down_revision = '42e1b5e7b295'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column
from sqlalchemy import String, Integer

role_table = table('role',
        column('id', Integer),
        column('name', String),
        column('description', String),
        )



def upgrade():
    op.bulk_insert(role_table, [{"name": "moteur", "description": ""}])



def downgrade():
    pass
