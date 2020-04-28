"""Add departement to ADS

Revision ID: 408130c68e5d
Revises: 2831056c7dd9
Create Date: 2015-04-20 10:02:05.862299

"""

# revision identifiers, used by Alembic.
revision = '408130c68e5d'
down_revision = '2831056c7dd9'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('conducteur', sa.Column('departement_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'conducteur', 'departement', ['departement_id'], ['id'])


def downgrade():
    op.drop_constraint(None, 'conducteur', type_='foreignkey')
    op.drop_column('conducteur', 'departement_id')
