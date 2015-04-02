"""Add auth token to user

Revision ID: c96866c372a
Revises: 4bf756d958a1
Create Date: 2015-04-02 10:15:46.138543

"""

# revision identifiers, used by Alembic.
revision = 'c96866c372a'
down_revision = '4bf756d958a1'

from alembic import op
import sqlalchemy as sa
import uuid


def upgrade():
    op.add_column('user', sa.Column('auth_token', sa.String(length=255),
        nullable=True))
    user = sa.sql.table('user', sa.sql.column('auth_token', sa.String),
            sa.sql.column('id', sa.Integer))
    for u in op.get_bind().execute(user.select()):
        op.execute(user.update().where(user.c.id == u.id).values(auth_token=str(uuid.uuid4)))
    op.alter_column('user', 'auth_token', nullable=False)


def downgrade():
    op.drop_column('user', 'auth_token')
