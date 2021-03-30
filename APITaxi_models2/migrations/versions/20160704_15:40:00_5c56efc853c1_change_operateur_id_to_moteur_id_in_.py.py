"""Change operateur_id to moteur_id in Customer

Revision ID: 5c56efc853c1
Revises: f0ae9448295b
Create Date: 2016-07-04 15:40:00.442373

"""

# revision identifiers, used by Alembic.
revision = '5c56efc853c1'
down_revision = 'f0ae9448295b'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.drop_constraint('customer_operateur_id_fkey', 'customer', type_='foreignkey')
    op.alter_column('customer', 'operateur_id', new_column_name='moteur_id')
    op.create_foreign_key('customer_primary_key', 'customer', 'user', ['moteur_id'], ['id'])


def downgrade():
    op.drop_constraint('customer_primary_key', 'customer', type_='foreignkey')
    op.alter_column('customer', 'moteur_id', new_column_name='operateur_id')
    op.create_foreign_key('customer_operateur_id_fkey', 'customer', 'user', ['operateur_id'], ['id'])
