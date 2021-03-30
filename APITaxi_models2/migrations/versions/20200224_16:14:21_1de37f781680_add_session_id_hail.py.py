""" Add session_id to Hail modeel

Revision ID: 1de37f781680
Revises: f8c0bde5d368
Create Date: 2020-02-24 16:14:21.149350

"""

# revision identifiers, used by Alembic.
revision = '1de37f781680'
down_revision = 'f8c0bde5d368'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('hail', sa.Column('session_id', sa.String(), server_default='', nullable=False))


def downgrade():
    op.drop_column('hail', 'session_id')
