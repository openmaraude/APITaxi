"""drop hail.change_to_xxx

Revision ID: 54e7b2b8da6d
Revises: 34a39e9fb39a
Create Date: 2021-03-01 14:39:19.254552

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '54e7b2b8da6d'
down_revision = '34a39e9fb39a'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('hail', 'change_to_failure')
    op.drop_column('hail', 'change_to_customer_on_board')
    op.drop_column('hail', 'change_to_sent_to_operator')
    op.drop_column('hail', 'change_to_accepted_by_taxi')
    op.drop_column('hail', 'change_to_timeout_taxi')
    op.drop_column('hail', 'change_to_declined_by_taxi')
    op.drop_column('hail', 'change_to_received_by_operator')
    op.drop_column('hail', 'change_to_timeout_accepted_by_customer')
    op.drop_column('hail', 'change_to_received_by_taxi')
    op.drop_column('hail', 'change_to_incident_taxi')
    op.drop_column('hail', 'change_to_accepted_by_customer')
    op.drop_column('hail', 'change_to_declined_by_customer')
    op.drop_column('hail', 'change_to_finished')
    op.drop_column('hail', 'change_to_timeout_customer')
    op.drop_column('hail', 'change_to_incident_customer')


def downgrade():
    op.add_column('hail', sa.Column('change_to_incident_customer', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('hail', sa.Column('change_to_timeout_customer', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('hail', sa.Column('change_to_finished', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('hail', sa.Column('change_to_declined_by_customer', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('hail', sa.Column('change_to_accepted_by_customer', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('hail', sa.Column('change_to_incident_taxi', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('hail', sa.Column('change_to_received_by_taxi', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('hail', sa.Column('change_to_timeout_accepted_by_customer', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('hail', sa.Column('change_to_received_by_operator', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('hail', sa.Column('change_to_declined_by_taxi', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('hail', sa.Column('change_to_timeout_taxi', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('hail', sa.Column('change_to_accepted_by_taxi', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('hail', sa.Column('change_to_sent_to_operator', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('hail', sa.Column('change_to_customer_on_board', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('hail', sa.Column('change_to_failure', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
