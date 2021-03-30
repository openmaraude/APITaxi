"""drop ZUPC obsolete columns

Revision ID: 5887f860f0ee
Revises: 9a7774e8336f
Create Date: 2021-02-17 08:05:19.276365

"""
from alembic import op
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '5887f860f0ee'
down_revision = '9a7774e8336f'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('ZUPC', 'zupc_id',
                    existing_type=postgresql.UUID(),
                    nullable=False)
    op.drop_index('zupc_shape_idx', table_name='ZUPC')
    op.drop_index('zupc_shape_igx', table_name='ZUPC')
    op.drop_constraint('zupc_parent_foreign_key', 'ZUPC', type_='foreignkey')
    op.drop_column('ZUPC', 'shape')
    op.drop_column('ZUPC', 'insee')
    op.drop_column('ZUPC', 'parent_id')


def downgrade():
    op.add_column('ZUPC', sa.Column('parent_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('ZUPC', sa.Column('insee', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('ZUPC', sa.Column('shape', geoalchemy2.types.Geography(geometry_type='MULTIPOLYGON', srid=4326, from_text='ST_GeogFromText', name='geography'), autoincrement=False, nullable=True))
    op.create_foreign_key('zupc_parent_foreign_key', 'ZUPC', 'ZUPC', ['parent_id'], ['id'])
    op.create_index('zupc_shape_igx', 'ZUPC', ['shape'], unique=False)
    op.create_index('zupc_shape_idx', 'ZUPC', ['shape'], unique=False)
    op.alter_column('ZUPC', 'zupc_id',
                    existing_type=postgresql.UUID(),
                    nullable=True)
