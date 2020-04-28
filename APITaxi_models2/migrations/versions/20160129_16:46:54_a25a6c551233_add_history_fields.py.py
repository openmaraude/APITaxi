"""Add history fields

Revision ID: a25a6c551233
Revises: a04da4b32a36
Create Date: 2016-01-29 16:46:54.522253

"""

# revision identifiers, used by Alembic.
revision = 'a25a6c551233'
down_revision = 'a04da4b32a36'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('hail', sa.Column('change_to_accepted_by_customer', sa.DateTime(), nullable=True))
    op.add_column('hail', sa.Column('change_to_accepted_by_taxi', sa.DateTime(), nullable=True))
    op.add_column('hail', sa.Column('change_to_declined_by_customer', sa.DateTime(), nullable=True))
    op.add_column('hail', sa.Column('change_to_declined_by_taxi', sa.DateTime(), nullable=True))
    op.add_column('hail', sa.Column('change_to_failure', sa.DateTime(), nullable=True))
    op.add_column('hail', sa.Column('change_to_incident_customer', sa.DateTime(), nullable=True))
    op.add_column('hail', sa.Column('change_to_incident_taxi', sa.DateTime(), nullable=True))
    op.add_column('hail', sa.Column('change_to_received_by_operator', sa.DateTime(), nullable=True))
    op.add_column('hail', sa.Column('change_to_received_by_taxi', sa.DateTime(), nullable=True))
    op.add_column('hail', sa.Column('change_to_sent_to_operator', sa.DateTime(), nullable=True))
    op.add_column('hail', sa.Column('change_to_timeout_customer', sa.DateTime(), nullable=True))
    op.add_column('hail', sa.Column('change_to_timeout_taxi', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('hail', 'change_to_timeout_taxi')
    op.drop_column('hail', 'change_to_timeout_customer')
    op.drop_column('hail', 'change_to_sent_to_operator')
    op.drop_column('hail', 'change_to_received_by_taxi')
    op.drop_column('hail', 'change_to_received_by_operator')
    op.drop_column('hail', 'change_to_incident_taxi')
    op.drop_column('hail', 'change_to_incident_customer')
    op.drop_column('hail', 'change_to_failure')
    op.drop_column('hail', 'change_to_declined_by_taxi')
    op.drop_column('hail', 'change_to_declined_by_customer')
    op.drop_column('hail', 'change_to_accepted_by_taxi')
    op.drop_column('hail', 'change_to_accepted_by_customer')
