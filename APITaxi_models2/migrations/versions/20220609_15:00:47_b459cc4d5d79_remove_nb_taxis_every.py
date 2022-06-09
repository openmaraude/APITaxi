"""Remove nb_taxis_every

Revision ID: b459cc4d5d79
Revises: bc136ac7ac92
Create Date: 2022-06-09 15:00:47.953466

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b459cc4d5d79'
down_revision = 'bc136ac7ac92'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index('nb_taxis_every_time', table_name='nb_taxis_every')
    op.drop_table('nb_taxis_every')


def downgrade():
    op.create_table('nb_taxis_every',
    sa.Column('measurement', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('time', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('value', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('insee', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('zupc', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('operator', sa.VARCHAR(), autoincrement=False, nullable=True)
    )
    op.create_index('nb_taxis_every_time', 'nb_taxis_every', ['time', 'measurement'], unique=False)
