"""Add stats view

Revision ID: 6f3683e7501
Revises: 463ab467b156
Create Date: 2015-08-17 11:19:54.401534

"""

# revision identifiers, used by Alembic.
revision = '6f3683e7501'
down_revision = '463ab467b156'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table('active_taxis',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('zupc_id', sa.Integer(), nullable=True),
    sa.Column('operator_id', sa.Integer(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.Column('nb_taxis', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_active_taxis_operator_id'), 'active_taxis', ['operator_id'], unique=False)
    op.create_index(op.f('ix_active_taxis_zupc_id'), 'active_taxis', ['zupc_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_active_taxis_zupc_id'), table_name='active_taxis')
    op.drop_index(op.f('ix_active_taxis_operator_id'), table_name='active_taxis')
    op.drop_table('active_taxis')
