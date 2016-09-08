"""Add new hail statuses

Revision ID: 3e54873a977a
Revises: e967c1579fef
Create Date: 2016-09-05 17:01:19.689634

"""

# revision identifiers, used by Alembic.

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = '3e54873a977a'
down_revision = 'e967c1579fef'
name = 'hail_status'
tmp_name = '_'+name
old_options =  [ 'emitted', 'received', 'sent_to_operator',
          'received_by_operator', 'received_by_taxi', 'timeout_taxi', 'accepted_by_taxi',
          'timeout_customer', 'incident_taxi', 'declined_by_taxi', 'accepted_by_customer',
          'incident_customer', 'declined_by_customer', 'outdated_customer',
          'outdated_taxi', 'failure', 'customer_banned']
new_statuses = ['finished', 'customer_on_board', 'timeout_accepted_by_customer']
new_options = old_options + new_statuses

old_type = sa.Enum(*old_options, name=name)
new_type = sa.Enum(*new_options, name=name)
tmp_type = sa.Enum(*new_options, name=tmp_name)

table_name = 'hail'
column_name = 'status'
tcr = sa.sql.table(table_name,
                   sa.Column(column_name, new_type, nullable=False))

def upgrade():
    op.add_column('taxi', sa.Column('current_hail_id', sa.String(), nullable=True))
    op.create_foreign_key('taxi_hail_id', 'taxi', 'hail', ['current_hail_id'], ['id'])
    tmp_type.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE {} ALTER COLUMN {} TYPE {}'
               ' USING status::text::{}'.format(table_name, column_name, tmp_name, tmp_name))
    old_type.drop(op.get_bind(), checkfirst=False)
    # Create and convert to the "new" status type
    new_type.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE {} ALTER COLUMN {} TYPE {}'
               ' USING status::text::{}'.format(table_name, column_name, name, name))
    tmp_type.drop(op.get_bind(), checkfirst=False)
    op.add_column('hail', sa.Column('change_to_customer_on_board', sa.DateTime(), nullable=True))
    op.add_column('hail', sa.Column('change_to_finished', sa.DateTime(), nullable=True))
    op.add_column('hail', sa.Column('change_to_timeout_accepted_by_customer', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_constraint('taxi_hail_id', 'taxi', type_='foreignkey')
    op.drop_column('taxi', 'current_hail_id')
    for status in new_statuses:
        op.execute(tcr.update().where(tcr.c.status==status)
                   .values(status='failure'))
    # Create a tempoary "_status" type, convert and drop the "new" type
    tmp_type.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE {} ALTER COLUMN {} TYPE {}'
               ' USING status::text::{}'.format(table_name, column_name, tmp_name, tmp_name))
    new_type.drop(op.get_bind(), checkfirst=False)
    # Create and convert to the "old" status type
    old_type.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE {} ALTER COLUMN {} TYPE {}'
               ' USING status::text::{}'.format(table_name, column_name, name, name))
    tmp_type.drop(op.get_bind(), checkfirst=False)
    op.drop_column('hail', 'change_to_timeout_accepted_by_customer')
    op.drop_column('hail', 'change_to_finished')
    op.drop_column('hail', 'change_to_customer_on_board')
