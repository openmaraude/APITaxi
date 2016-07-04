"""Add reprieve and ban

Revision ID: f0ae9448295b
Revises: bc1f34a0615a
Create Date: 2016-07-04 11:19:22.508966

"""

# revision identifiers, used by Alembic.
revision = 'f0ae9448295b'
down_revision = 'bc1f34a0615a'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('customer', sa.Column('ban_begin', sa.DateTime(), nullable=True))
    op.add_column('customer', sa.Column('ban_end', sa.DateTime(), nullable=True))
    op.add_column('customer', sa.Column('phone_number', sa.String(), nullable=True))
    op.add_column('customer', sa.Column('reprieve_begin', sa.DateTime(), nullable=True))
    op.add_column('customer', sa.Column('reprieve_end', sa.DateTime(), nullable=True))
    op.drop_column('customer', 'nb_sanctions')


def downgrade():
    op.add_column('customer', sa.Column('nb_sanctions', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_column('customer', 'reprieve_end')
    op.drop_column('customer', 'reprieve_begin')
    op.drop_column('customer', 'phone_number')
    op.drop_column('customer', 'ban_end')
    op.drop_column('customer', 'ban_begin')
