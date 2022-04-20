"""Replace influx

Revision ID: ab94c984068e
Revises: da94441f919f
Create Date: 2022-04-20 13:51:01.952080

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ab94c984068e'
down_revision = 'da94441f919f'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'nb_taxis_every',
        sa.Column('measurement', sa.Integer(), nullable=False),
        sa.Column('time', sa.DateTime(), nullable=False),
        sa.Column('value', sa.Integer(), nullable=False),
        sa.Column('insee', sa.String(), nullable=True),
        sa.Column('zupc', sa.String(), nullable=True),
        sa.Column('operator', sa.String(), nullable=True)
    )
    op.create_index('nb_taxis_every_time', 'nb_taxis_every', ['time', 'measurement'], unique=False)


def downgrade():
    op.drop_index('nb_taxis_every_time', table_name='nb_taxis_every')
    op.drop_table('nb_taxis_every')
