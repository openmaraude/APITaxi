"""Change shape type, add parent and insee

Revision ID: 2e65dbaa935
Revises: 4190b0aefe23
Create Date: 2015-06-29 12:23:13.581187

"""

# revision identifiers, used by Alembic.
revision = '2e65dbaa935'
down_revision = '3183d344740d'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2 as ga
parent_zupc = 'zupc_parent_foreign_key'

def upgrade():
    op.add_column('ZUPC', sa.Column('insee', sa.String(), nullable=True))
    op.add_column('ZUPC', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.create_foreign_key(parent_zupc, 'ZUPC', 'ZUPC', ['parent_id'], ['id'])
    op.drop_column('ZUPC', 'shape')
    op.add_column('ZUPC', sa.Column('shape',
        ga.Geography(geometry_type='MULTIPOLYGON', srid=4326,
        spatial_index=False)))


def downgrade():
    op.drop_constraint(parent_zupc, 'ZUPC', type_='foreignkey')
    op.drop_column('ZUPC', 'parent_id')
    op.drop_column('ZUPC', 'insee')
    op.drop_column('ZUPC', 'shape')
    op.add_column('ZUPC', sa.Column('shape', sa.String()))
