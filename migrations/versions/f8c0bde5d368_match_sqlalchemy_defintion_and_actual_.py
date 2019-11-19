"""Match sqlalchemy defintion and actual schema

Revision ID: f8c0bde5d368
Revises: ae904ac154cf
Create Date: 2019-11-19 11:24:40.555110

"""

# revision identifiers, used by Alembic.
revision = 'f8c0bde5d368'
down_revision = 'ae904ac154cf'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.alter_column('ADS', 'added_via',
               existing_type=postgresql.ENUM('form', 'api', name='via'),
               nullable=False)


def downgrade():
    op.alter_column('ADS', 'added_via',
               existing_type=postgresql.ENUM('form', 'api', name='via'),
               nullable=True)
