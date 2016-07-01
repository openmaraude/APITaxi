"""Add retrieve and ban

Revision ID: d889513cc856
Revises: bc1f34a0615a
Create Date: 2016-07-01 15:21:50.212960

"""

# revision identifiers, used by Alembic.
revision = 'd889513cc856'
down_revision = 'bc1f34a0615a'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('user', sa.Column('ban_begin', sa.DateTime(), nullable=True))
    op.add_column('user', sa.Column('ban_end', sa.DateTime(), nullable=True))
    op.add_column('user', sa.Column('ban_length', sa.Integer(), nullable=True))
    op.add_column('user', sa.Column('reprieve_begin', sa.DateTime(), nullable=True))
    op.add_column('user', sa.Column('reprieve_end', sa.DateTime(), nullable=True))
    op.add_column('user', sa.Column('reprieve_length', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('user', 'reprieve_length')
    op.drop_column('user', 'reprieve_end')
    op.drop_column('user', 'reprieve_begin')
    op.drop_column('user', 'ban_length')
    op.drop_column('user', 'ban_end')
    op.drop_column('user', 'ban_begin')
