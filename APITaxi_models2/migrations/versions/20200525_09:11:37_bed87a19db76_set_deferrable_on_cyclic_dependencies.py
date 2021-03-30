"""Set deferrable on cyclic dependencies

Revision ID: bed87a19db76
Revises: 1de37f781680
Create Date: 2020-05-25 09:11:37.699004

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'bed87a19db76'
down_revision = '1de37f781680'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('hail_taxi_relation', 'hail', type_='foreignkey')
    op.create_foreign_key('hail_taxi_relation', 'hail', 'taxi', ['taxi_id'], ['id'], deferrable=True)
    op.drop_constraint('taxi_hail_id', 'taxi', type_='foreignkey')
    op.create_foreign_key('taxi_hail_id', 'taxi', 'hail', ['current_hail_id'], ['id'], deferrable=True, use_alter=True)


def downgrade():
    op.drop_constraint('taxi_hail_id', 'taxi', type_='foreignkey')
    op.create_foreign_key('taxi_hail_id', 'taxi', 'hail', ['current_hail_id'], ['id'])
    op.drop_constraint('hail_taxi_relation', 'hail', type_='foreignkey')
    op.create_foreign_key('hail_taxi_relation', 'hail', 'taxi', ['taxi_id'], ['id'])
