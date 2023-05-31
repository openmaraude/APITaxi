"""Add address field in hails

Revision ID: dcf00265e40
Revises: 586aded58391
Create Date: 2015-06-12 10:21:16.569658

"""

# revision identifiers, used by Alembic.
revision = 'dcf00265e40'
down_revision = '586aded58391'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('hail', sa.Column('customer_address', sa.String()))
    op.execute(sa.text('UPDATE hail SET customer_address=\'\''))
    op.alter_column('hail', 'customer_address', nullable=False)


def downgrade():
    op.drop_column('hail', 'customer_address')
