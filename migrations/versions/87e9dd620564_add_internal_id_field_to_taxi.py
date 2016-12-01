"""Add internal_id field to taxi

Revision ID: 87e9dd620564
Revises: bb73d477a1c4
Create Date: 2016-12-01 10:52:02.029281

"""

# revision identifiers, used by Alembic.
revision = '87e9dd620564'
down_revision = 'bb73d477a1c4'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('taxi', sa.Column('internal_id', sa.String(), nullable=True))


def downgrade():
    op.drop_column('taxi', 'internal_id')
