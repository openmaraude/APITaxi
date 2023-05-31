"""Fill empty added_at date

Revision ID: 71cacff30853
Revises: d26b4a2cc2ef
Create Date: 2016-04-04 16:43:45.040889

"""

# revision identifiers, used by Alembic.
revision = '71cacff30853'
down_revision = 'd26b4a2cc2ef'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime


def upgrade():
    when = datetime(2015, 1, 1)
    op.execute(sa.text('UPDATE customer SET added_at = \'2015-1-1\' WHERE added_at IS NULL'))
    op.execute(sa.text('UPDATE hail SET added_at = \'2015-1-1\' WHERE added_at IS NULL'))
    op.execute(sa.text('UPDATE "ADS" SET added_at = \'2015-1-1\' WHERE added_at IS NULL'))
    op.execute(sa.text('UPDATE driver SET added_at = \'2015-1-1\' WHERE added_at IS NULL'))
    op.execute(sa.text('UPDATE taxi SET added_at = \'2015-1-1\' WHERE added_at IS NULL'))
    op.execute(sa.text('UPDATE vehicle_description SET added_at = \'2015-1-1\' WHERE added_at IS NULL'))


def downgrade():
    pass
