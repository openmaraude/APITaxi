"""Station models

Revision ID: 7e794be3bf55
Revises: 4f97b4438c18
Create Date: 2021-04-13 11:52:03.672999

"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision = '7e794be3bf55'
down_revision = 'b459cc4d5d79'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'station',
        sa.Column('added_at', sa.DateTime(), nullable=True),
        # XXX Duplicating the Enum again because it's not smart enough to reuse if exists
        sa.Column('added_via', sa.Enum('form', 'api', name='sources_station'), nullable=False),
        sa.Column('source', sa.String(length=255), nullable=False),
        sa.Column('last_update_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('address', sa.String(), nullable=False),
        sa.Column('town_id', sa.Integer(), nullable=False),
        sa.Column('places', sa.Integer(), nullable=False),
        sa.Column('location', geoalchemy2.types.Geography(srid=4326, from_text='ST_GeogFromText', name='geography'), nullable=False),
        sa.Column('call_number', sa.String(length=10), nullable=True),
        sa.Column('info', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['town_id'], ['town.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('station')
