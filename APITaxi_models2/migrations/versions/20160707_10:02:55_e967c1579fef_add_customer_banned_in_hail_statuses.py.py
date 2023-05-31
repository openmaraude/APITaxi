"""Add customer banned in hail statuses

Revision ID: e967c1579fef
Revises: 5c56efc853c1
Create Date: 2016-07-07 10:02:55.399540

"""

# revision identifiers, used by Alembic.

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = 'e967c1579fef'
down_revision = '5c56efc853c1'
name = 'hail_status'
tmp_name = '_'+name
old_options =  [ 'emitted', 'received', 'sent_to_operator',
          'received_by_operator', 'received_by_taxi', 'timeout_taxi', 'accepted_by_taxi',
          'timeout_customer', 'incident_taxi', 'declined_by_taxi', 'accepted_by_customer',
          'incident_customer', 'declined_by_customer', 'outdated_customer',
          'outdated_taxi', 'failure']
new_options = old_options + ['customer_banned']

old_type = sa.Enum(*old_options, name=name)
new_type = sa.Enum(*new_options, name=name)
tmp_type = sa.Enum(*new_options, name=tmp_name)

table_name = 'hail'
column_name = 'status'

tcr = sa.sql.table(table_name,
                  sa.Column(column_name, new_type, nullable=False))

def upgrade():
    tmp_type.create(op.get_bind(), checkfirst=False)
    op.execute(sa.text('ALTER TABLE {} ALTER COLUMN {} TYPE {}'
               ' USING status::text::{}'.format(table_name, column_name, tmp_name, tmp_name)))
    old_type.drop(op.get_bind(), checkfirst=False)
    # Create and convert to the "new" status type
    new_type.create(op.get_bind(), checkfirst=False)
    op.execute(sa.text('ALTER TABLE {} ALTER COLUMN {} TYPE {}'
               ' USING status::text::{}'.format(table_name, column_name, name, name)))
    tmp_type.drop(op.get_bind(), checkfirst=False)

def downgrade():
    op.execute(tcr.update().where(tcr.c.status=='customer_banned')
               .values(status='failure'))
    # Create a tempoary "_status" type, convert and drop the "new" type
    tmp_type.create(op.get_bind(), checkfirst=False)
    op.execute(sa.text('ALTER TABLE {} ALTER COLUMN {} TYPE {}'
               ' USING status::text::{}'.format(table_name, column_name, tmp_name, tmp_name)))
    new_type.drop(op.get_bind(), checkfirst=False)
    # Create and convert to the "old" status type
    old_type.create(op.get_bind(), checkfirst=False)
    op.execute(sa.text('ALTER TABLE {} ALTER COLUMN {} TYPE {}'
               ' USING status::text::{}'.format(table_name, column_name, name, name)))
    tmp_type.drop(op.get_bind(), checkfirst=False)
