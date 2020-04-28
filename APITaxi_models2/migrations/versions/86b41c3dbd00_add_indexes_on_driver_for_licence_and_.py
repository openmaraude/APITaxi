"""Add indexes on driver for licence and departement

Revision ID: 86b41c3dbd00
Revises: ccd5b0142a76
Create Date: 2019-10-21 15:55:35.965422

"""

# revision identifiers, used by Alembic.
revision = '86b41c3dbd00'
down_revision = 'ccd5b0142a76'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_index('driver_departement_id_idx', 'driver', ['departement_id'], unique=False)
    op.create_index('driver_professional_licence_idx', 'driver', ['professional_licence'], unique=False)


def downgrade():
    op.drop_index('driver_professional_licence_idx', table_name='driver')
    op.drop_index('driver_departement_id_idx', table_name='driver')
