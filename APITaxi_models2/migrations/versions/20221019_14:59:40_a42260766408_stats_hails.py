"""stats hails

Revision ID: a42260766408
Revises: 4069c2c08c49
Create Date: 2022-10-19 14:59:40.213185

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a42260766408'
down_revision = '4d58dd8dee5f'
branch_labels = None
depends_on = None


def upgrade():
    sources_enum = postgresql.ENUM('form', 'api', name='via', create_type=False)

    op.create_table('stats_hails',
        sa.Column('added_at', sa.DateTime(), nullable=False),
        sa.Column('added_via', sources_enum, nullable=False),
        sa.Column('source', sa.String(length=255), nullable=False),
        sa.Column('last_update_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('moteur', sa.String(), nullable=False),
        sa.Column('operateur', sa.String(), nullable=False),
        sa.Column('incident_customer_reason', sa.String(), nullable=True),
        sa.Column('incident_taxi_reason', sa.String(), nullable=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('insee', sa.String(), nullable=True),
        sa.Column('taxi_hash', sa.String(), nullable=True),
        sa.Column('reporting_customer', sa.Boolean(), nullable=True),
        sa.Column('reporting_customer_reason', sa.String(), nullable=True),
        sa.Column('received', sa.DateTime(), nullable=True),
        sa.Column('sent_to_operator', sa.DateTime(), nullable=True),
        sa.Column('received_by_operator', sa.DateTime(), nullable=True),
        sa.Column('received_by_taxi', sa.DateTime(), nullable=True),
        sa.Column('accepted_by_taxi', sa.DateTime(), nullable=True),
        sa.Column('accepted_by_customer', sa.DateTime(), nullable=True),
        sa.Column('declined_by_taxi', sa.DateTime(), nullable=True),
        sa.Column('declined_by_customer', sa.DateTime(), nullable=True),
        sa.Column('timeout_taxi', sa.DateTime(), nullable=True),
        sa.Column('timeout_customer', sa.DateTime(), nullable=True),
        sa.Column('incident_taxi', sa.DateTime(), nullable=True),
        sa.Column('incident_customer', sa.DateTime(), nullable=True),
        sa.Column('customer_on_board', sa.DateTime(), nullable=True),
        sa.Column('finished', sa.DateTime(), nullable=True),
        sa.Column('failure', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id', 'added_at', name='stats_hails_pkey')
    )
    op.execute("SELECT create_hypertable('stats_hails', 'added_at')")

def downgrade():
    op.drop_table('stats_hails')
