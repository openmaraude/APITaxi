"""archive hails

Revision ID: da94441f919f
Revises: 51c630a38d3c
Create Date: 2022-03-16 13:46:13.409774

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'da94441f919f'
down_revision = '51c630a38d3c'
branch_labels = None
depends_on = None


def upgrade():
    sources_enum = postgresql.ENUM('form', 'api', name='via', create_type=False)

    op.create_table(
        'archived_hail',
        sa.Column('added_at', sa.DateTime(), nullable=True),
        sa.Column('added_via', sources_enum, nullable=False),
        sa.Column('source', sa.String(length=255), nullable=False),
        sa.Column('last_update_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('moteur', sa.String(), nullable=False),
        sa.Column('operateur', sa.String(), nullable=False),
        sa.Column('incident_customer_reason', sa.String()),
        sa.Column('incident_taxi_reason', sa.String()),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('insee', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.add_column('hail', sa.Column('blurred', sa.Boolean(), server_default='false', nullable=True))


def downgrade():
    op.drop_column('hail', 'blurred')
    op.drop_table('archived_hail')
