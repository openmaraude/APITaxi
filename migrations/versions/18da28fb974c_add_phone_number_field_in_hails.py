"""Add phone_number field in hails

Revision ID: 18da28fb974c
Revises: dcf00265e40
Create Date: 2015-06-12 11:32:54.984209

"""

# revision identifiers, used by Alembic.
revision = '18da28fb974c'
down_revision = 'dcf00265e40'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('hail', sa.Column('customer_phone_number', sa.String(), nullable=True))
    op.execute('UPDATE hail SET customer_phone_number=\'\'')
    op.alter_column('hail', 'customer_phone_number', nullable=False)


def downgrade():
    op.drop_column('hail', 'customer_phone_number')
