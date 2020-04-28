"""Add indexes on ADS for numero and insee

Revision ID: 34c2049aaee2
Revises: e187aca7c77a
Create Date: 2019-10-21 16:35:48.431148

"""

# revision identifiers, used by Alembic.
revision = '34c2049aaee2'
down_revision = 'e187aca7c77a'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_index('ads_insee_index', 'ADS', ['insee'], unique=False)
    op.create_index('ads_numero_index', 'ADS', ['numero'], unique=False)


def downgrade():
    op.drop_index('ads_numero_index', table_name='ADS')
    op.drop_index('ads_insee_index', table_name='ADS')
