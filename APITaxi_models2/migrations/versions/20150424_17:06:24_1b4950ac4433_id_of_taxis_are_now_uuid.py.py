"""Id of taxis are now uuid

Revision ID: 1b4950ac4433
Revises: 3e8b56d60090
Create Date: 2015-04-24 17:06:24.972421

"""

# revision identifiers, used by Alembic.
revision = '1b4950ac4433'
down_revision = '3e8b56d60090'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.alter_column('taxi', 'id', type_=sa.String, existing_type=sa.INTEGER,
            nullable=False)
    op.alter_column('hail', 'taxi_id', type_=sa.String,
            existing_type=sa.INTEGER, nullable=False)
    op.alter_column('ADS', 'numero', type_=sa.String, existing_type=sa.INTEGER,
            nullable=False)
    op.alter_column('ADS', 'insee', type_=sa.String, existing_type=sa.INTEGER,
            nullable=False)

def downgrade():
    op.execute('ALTER TABLE taxi ALTER COLUMN id TYPE INTEGER'
            ' USING id::INTEGER');
    op.execute('ALTER TABLE hail ALTER COLUMN taxi_id TYPE INTEGER'
            ' USING taxi_id::INTEGER');
    op.execute('ALTER TABLE "ADS" ALTER COLUMN numero TYPE INTEGER'
            ' USING numero::INTEGER');
    op.execute('ALTER TABLE "ADS" ALTER COLUMN insee TYPE INTEGER'
            ' USING insee::INTEGER');
