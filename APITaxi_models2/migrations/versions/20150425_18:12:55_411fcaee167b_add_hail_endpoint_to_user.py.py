"""Add hail_endpoint to user

Revision ID: 411fcaee167b
Revises: 26311efc301f
Create Date: 2015-04-25 18:12:55.584619

"""

# revision identifiers, used by Alembic.
revision = '411fcaee167b'
down_revision = '26311efc301f'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

old_options = ('emitted', 'received',
    'sent_to_operator', 'received_by_operator',
    'received_by_taxi', 'accepted_by_taxi',
    'declined_by_taxi', 'incident_customer',
    'incident_taxi', 'timeout_customer', 'timeout_taxi',
     'outdated_customer', 'outdated_taxi')
new_options = sorted(old_options + ('failure',))

old_type = sa.Enum(*old_options, name='hail_status')
new_type = sa.Enum(*new_options, name='hail_status')
tmp_type = sa.Enum(*new_options, name='_status')

tcr = sa.sql.table('hail',
                   sa.Column('status', new_type, nullable=False))

def upgrade():
    tmp_type.create(op.get_bind(), checkfirst=False)
    op.execute(sa.text('ALTER TABLE hail ALTER COLUMN status TYPE _status'
               ' USING status::text::_status'))
    old_type.drop(op.get_bind(), checkfirst=False)
    new_type.create(op.get_bind(), checkfirst=False)
    op.execute(sa.text('ALTER TABLE hail ALTER COLUMN status TYPE hail_status'
               ' USING status::text::hail_status'))
    tmp_type.drop(op.get_bind(), checkfirst=False)


def downgrade():
    op.execute(hail.update().where(hail.c.status=='failure')
               .values(status='outdated_taxi'))
    tmp_type.create(op.get_bind(), checkfirst=False)
    op.execute(sa.text('ALTER TABLE hail ALTER COLUMN status TYPE hail__status'
               ' USING status::text::hail__status'))
    new_type.drop(op.get_bind(), checkfirst=False)
    old_type.create(op.get_bind(), checkfirst=False)
    op.execute(sa.text('ALTER TABLE hail ALTER COLUMN status TYPE hail_status'
               ' USING status::text::hail_status'))
    tmp_type.drop(op.get_bind(), checkfirst=False)
