"""Stats Searches

Revision ID: 84b3ccf6a8fa
Revises: e8ca55149b91
Create Date: 2024-09-09 09:51:35.426327

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '84b3ccf6a8fa'
down_revision = 'e8ca55149b91'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('stats_searches',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('lon', sa.Float),
        sa.Column('lat', sa.Float),
        sa.Column('insee', sa.String(length=5), nullable=False),
        sa.Column('town', sa.String, nullable=False),
        sa.Column('moteur', sa.String(), nullable=False),
        sa.Column('taxis_found', sa.Integer(), nullable=False),
        sa.Column('closest_taxi', sa.Float(), nullable=True),
        sa.Column('added_at', sa.DateTime(), nullable=False),
        sa.Column('taxis_seen', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id', 'added_at', name='stats_searches_pkey')
    )

    op.execute("SELECT create_hypertable('stats_searches', 'added_at')")



def downgrade():
    op.drop_table('stats_searches')
