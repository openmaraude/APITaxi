"""Add unique constraint Departement.numero

Revision ID: ae904ac154cf
Revises: 75704b2e975e
Create Date: 2019-10-24 11:12:58.985106

"""

# revision identifiers, used by Alembic.
revision = 'ae904ac154cf'
down_revision = '75704b2e975e'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

constraint_name = 'departement_numero_unique'

def upgrade():
    op.create_unique_constraint(constraint_name, 'departement', ['numero'])


def downgrade():
    op.drop_constraint(constraint_name, 'departement', type_='unique')

