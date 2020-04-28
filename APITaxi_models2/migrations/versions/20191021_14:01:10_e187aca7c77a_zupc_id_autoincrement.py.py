"""ZUPC.id autoincrement

Revision ID: e187aca7c77a
Revises: ccd5b0142a76
Create Date: 2019-10-21 14:01:10.406983

"""

# revision identifiers, used by Alembic.
revision = 'e187aca7c77a'
down_revision = '86b41c3dbd00'

from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import Sequence, CreateSequence, DropSequence
import sqlalchemy as sa


def upgrade():
    op.execute('''
        CREATE SEQUENCE ZUPC_id_seq;
        ALTER TABLE "ZUPC" ALTER COLUMN id SET DEFAULT nextval('ZUPC_id_seq');
    ''')


def downgrade():
    op.execute('''
        ALTER TABLE "ZUPC" ALTER COLUMN id DROP DEFAULT;
        DROP SEQUENCE ZUPC_id_seq
    ''')
