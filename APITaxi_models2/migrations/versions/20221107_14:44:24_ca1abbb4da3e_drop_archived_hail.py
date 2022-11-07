"""drop archived hail

Revision ID: ca1abbb4da3e
Revises: a42260766408
Create Date: 2022-11-07 14:44:24.499245

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ca1abbb4da3e'
down_revision = 'a42260766408'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('archived_hail')


def downgrade():
    op.create_table('archived_hail',
        sa.Column('added_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
        sa.Column('added_via', postgresql.ENUM('form', 'api', name='via'), autoincrement=False, nullable=False),
        sa.Column('source', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
        sa.Column('last_update_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('id', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('status', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('moteur', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('operateur', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('incident_customer_reason', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('incident_taxi_reason', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('session_id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column('insee', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint('id', name='archived_hail_pkey')
    )
