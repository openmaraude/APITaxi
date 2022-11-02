"""require added_at

Revision ID: 4d58dd8dee5f
Revises: 4069c2c08c49
Create Date: 2022-11-02 10:33:45.425584

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4d58dd8dee5f'
down_revision = '4069c2c08c49'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('ADS', 'added_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('archived_hail', 'added_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('customer', 'added_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('driver', 'added_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('hail', 'added_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('taxi', 'added_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('vehicle_description', 'added_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)


def downgrade():
    op.alter_column('vehicle_description', 'added_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.alter_column('taxi', 'added_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.alter_column('hail', 'added_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.alter_column('driver', 'added_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.alter_column('customer', 'added_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.alter_column('archived_hail', 'added_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.alter_column('ADS', 'added_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
