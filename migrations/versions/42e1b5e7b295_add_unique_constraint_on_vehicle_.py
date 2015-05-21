"""Add unique constraint on vehicle description

Revision ID: 42e1b5e7b295
Revises: 1ee1afe31462
Create Date: 2015-05-19 10:28:19.227811

"""

# revision identifiers, used by Alembic.
revision = '42e1b5e7b295'
down_revision = '1ee1afe31462'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.execute("""
        DELETE FROM vehicle_description vd USING vehicle_description vd2
          WHERE vd.vehicle_id = vd2.vehicle_id AND vd.added_by = vd2.added_by
          AND vd.id < vd2.id;
        """)
    op.create_unique_constraint('uq_vehicle_description', 'vehicle_description',
            ['vehicle_id', 'added_by'])


def downgrade():
    op.drop_constraint('uq_vehicle_description', 'vehicle_description')
