"""Create Town

Revision ID: 918717b2e507
Revises: a3df227b3e08
Create Date: 2021-02-02 08:38:18.821624

"""
from alembic import op
import geoalchemy2
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '918717b2e507'
down_revision = 'a3df227b3e08'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'town',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('insee', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('shape', geoalchemy2.types.Geography(geometry_type='MULTIPOLYGON', srid=4326, from_text='ST_GeogFromText', name='geography'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('insee')
    )


def downgrade():
    op.drop_table('town')
