"""New revision

Revision ID: 7069a8583248
Revises: ab94c984068e
Create Date: 2022-05-11 16:49:57.708645

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7069a8583248'
down_revision = 'ab94c984068e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('stats_day',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_day_insee',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('insee', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_day_operator',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('operator', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_day_operator_insee',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('insee', sa.String(), nullable=False),
    sa.Column('operator', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_day_operator_zupc',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('zupc', sa.String(), nullable=False),
    sa.Column('operator', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_day_zupc',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('zupc', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_hour',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_hour_insee',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('insee', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_hour_operator',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('operator', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_hour_operator_insee',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('insee', sa.String(), nullable=False),
    sa.Column('operator', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_hour_operator_zupc',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('zupc', sa.String(), nullable=False),
    sa.Column('operator', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_hour_zupc',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('zupc', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_minute',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_minute_insee',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('insee', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_minute_operator',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('operator', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_minute_operator_insee',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('insee', sa.String(), nullable=False),
    sa.Column('operator', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_minute_operator_zupc',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('zupc', sa.String(), nullable=False),
    sa.Column('operator', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_minute_zupc',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('zupc', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_week',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_week_insee',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('insee', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_week_operator',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('operator', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_week_operator_insee',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('insee', sa.String(), nullable=False),
    sa.Column('operator', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_week_operator_zupc',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('zupc', sa.String(), nullable=False),
    sa.Column('operator', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stats_week_zupc',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('zupc', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('stats_week_zupc')
    op.drop_table('stats_week_operator_zupc')
    op.drop_table('stats_week_operator_insee')
    op.drop_table('stats_week_operator')
    op.drop_table('stats_week_insee')
    op.drop_table('stats_week')
    op.drop_table('stats_minute_zupc')
    op.drop_table('stats_minute_operator_zupc')
    op.drop_table('stats_minute_operator_insee')
    op.drop_table('stats_minute_operator')
    op.drop_table('stats_minute_insee')
    op.drop_table('stats_minute')
    op.drop_table('stats_hour_zupc')
    op.drop_table('stats_hour_operator_zupc')
    op.drop_table('stats_hour_operator_insee')
    op.drop_table('stats_hour_operator')
    op.drop_table('stats_hour_insee')
    op.drop_table('stats_hour')
    op.drop_table('stats_day_zupc')
    op.drop_table('stats_day_operator_zupc')
    op.drop_table('stats_day_operator_insee')
    op.drop_table('stats_day_operator')
    op.drop_table('stats_day_insee')
    op.drop_table('stats_day')
