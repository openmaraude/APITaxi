"""Station models

Revision ID: 7e794be3bf55
Revises: 4f97b4438c18
Create Date: 2021-04-13 11:52:03.672999

"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7e794be3bf55'
down_revision = 'ca1abbb4da3e'
branch_labels = None
depends_on = None


def upgrade():
    sources_enum = postgresql.ENUM('form', 'api', name='via', create_type=False)

    op.create_table(
        'station',
        sa.Column('added_at', sa.DateTime(), nullable=True),
        sa.Column('added_via', sources_enum, nullable=False),
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
