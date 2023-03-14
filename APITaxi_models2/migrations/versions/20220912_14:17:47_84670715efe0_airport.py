"""Exclude zones like airports

Revision ID: 84670715efe0
Revises: 5001a09d73d3
Create Date: 2022-09-12 14:17:47.114384

"""
from alembic import op
import geoalchemy2.types
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '84670715efe0'
down_revision = '861188cd0769'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('exclusion',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('shape', geoalchemy2.types.Geography(geometry_type='MULTIPOLYGON', srid=4326, from_text='ST_GeogFromText', name='geography'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    # Seems to be automatically created
    # op.create_index('idx_exclusion_shape', 'exclusion', ['shape'], unique=False, postgresql_using='gist')


def downgrade():
    op.drop_index('idx_exclusion_shape', table_name='exclusion', postgresql_using='gist')
    op.drop_table('exclusion')
