"""Add index on Departement for numero

Revision ID: 75704b2e975e
Revises: 34c2049aaee2
Create Date: 2019-10-22 17:27:10.925104

"""

# revision identifiers, used by Alembic.
revision = '75704b2e975e'
down_revision = '34c2049aaee2'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_index('departement_numero_index', 'departement', ['numero'], unique=False)


def downgrade():
    op.drop_index('departement_numero_index', table_name='departement')
