"""Add more descriptions on user

Revision ID: 586aded58391
Revises: 3bcda5bdca8c
Create Date: 2015-06-08 11:12:18.780839

"""

# revision identifiers, used by Alembic.
revision = '586aded58391'
down_revision = '3bcda5bdca8c'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('user', sa.Column('email_customer', sa.String(), nullable=True))
    op.add_column('user', sa.Column('email_technical', sa.String(), nullable=True))
    op.add_column('user', sa.Column('hail_endpoint_production', sa.String(), nullable=True))
    op.add_column('user', sa.Column('hail_endpoint_staging', sa.String(), nullable=True))
    op.add_column('user', sa.Column('hail_endpoint_testing', sa.String(), nullable=True))
    op.add_column('user', sa.Column('phone_number_customer', sa.String(), nullable=True))
    op.add_column('user', sa.Column('phone_number_technical', sa.String(), nullable=True))
    op.drop_column('user', 'phone_number')
    op.drop_column('user', 'hail_endpoint')


def downgrade():
    op.add_column('user', sa.Column('hail_endpoint', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('user', sa.Column('phone_number', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_column('user', 'phone_number_technical')
    op.drop_column('user', 'phone_number_customer')
    op.drop_column('user', 'hail_endpoint_testing')
    op.drop_column('user', 'hail_endpoint_staging')
    op.drop_column('user', 'hail_endpoint_production')
    op.drop_column('user', 'email_technical')
    op.drop_column('user', 'email_customer')
