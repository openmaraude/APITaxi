"""Add ZUPC active

Revision ID: 4d09adff27fb
Revises: 14b6c76f933f
Create Date: 2015-11-18 10:32:22.966783

"""

# revision identifiers, used by Alembic.
revision = '4d09adff27fb'
down_revision = '14b6c76f933f'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('ZUPC', sa.Column('active', sa.Boolean(), nullable=True))
    op.execute(sa.text('UPDATE "ZUPC" set active = False;'))
    op.alter_column('ZUPC', 'active', nullable=False)


def downgrade():
    op.drop_column('ZUPC', 'active')
