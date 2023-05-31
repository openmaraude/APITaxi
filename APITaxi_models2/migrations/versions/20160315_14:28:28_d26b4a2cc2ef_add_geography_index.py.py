"""Add geography index

Revision ID: d26b4a2cc2ef
Revises: a25a6c551233
Create Date: 2016-03-15 14:28:28.132301

"""

# revision identifiers, used by Alembic.
revision = 'd26b4a2cc2ef'
down_revision = 'a25a6c551233'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.execute(sa.text('CREATE INDEX zupc_shape_igx ON "ZUPC" USING GIST (shape)'))
    op.execute(sa.text('CLUSTER "ZUPC" USING zupc_shape_igx'))


def downgrade():
    op.execute(sa.text('DROP INDEX zupc_shape_igx'))
