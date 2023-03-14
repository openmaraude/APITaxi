"""activity logs

Revision ID: 43685d1824b7
Revises: 861188cd0769
Create Date: 2023-02-28 11:06:53.959875

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '43685d1824b7'
down_revision = '84670715efe0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('activity_log',
        sa.Column('time', sa.DateTime(), nullable=False),
        sa.Column('resource', sa.String(), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('extra', postgresql.JSONB(), nullable=True),
    )
    op.execute("SELECT create_hypertable('activity_log', 'time')")
    op.execute("""
        ALTER TABLE activity_log SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'resource, resource_id',
            timescaledb.compress_orderby = 'time DESC'
        )
    """)
    op.execute("SELECT add_compression_policy('activity_log', INTERVAL '7 days')")
    op.execute("SELECT add_retention_policy('activity_log', INTERVAL '2 months')")

def downgrade():
    op.drop_table('activity_log')
