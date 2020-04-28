"""operateur id is now a foreign_key

Revision ID: b0eeeeb2671
Revises: 411fcaee167b
Create Date: 2015-04-25 19:44:34.337983

"""

# revision identifiers, used by Alembic.
revision = 'b0eeeeb2671'
down_revision = '411fcaee167b'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_foreign_key('hail_operateur_id', 'hail', 'user', ['operateur_id'], ['id'])


def downgrade():
    op.drop_constraint('hail_operateur_id', 'hail', type_='foreignkey')
