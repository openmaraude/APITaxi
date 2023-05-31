"""Encrypt password

Revision ID: 48a67526c4d7
Revises: 4e62a5e5f592
Create Date: 2015-05-28 12:29:23.166520

"""

# revision identifiers, used by Alembic.
revision = '48a67526c4d7'
down_revision = '4e62a5e5f592'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from flask_security.utils import hash_password

user_table = sa.Table('user', sa.MetaData(),
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('password', sa.String)
)


def upgrade():
    conn = op.get_bind()
    for u in conn.execute(user_table.select()):
        conn.execute(sa.text('UPDATE "user" set password=:password where id=:id', {'password': hash_password(u[1]), 'id': u[0]}))


def downgrade():
    pass
