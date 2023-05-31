"""add declined by customer

Revision ID: 53c6b52778a7
Revises: 450554023cb2
Create Date: 2015-07-16 17:38:37.471542

"""

# revision identifiers, used by Alembic.
revision = '53c6b52778a7'
down_revision = '4808a446539c'

from alembic import op
import sqlalchemy as sa
old_options = ( 'emitted', 'received',
    'sent_to_operator', 'received_by_operator',
    'received_by_taxi',
    'accepted_by_taxi',
    'declined_by_taxi', 'declined_by_customer',
    'incident_customer', 'incident_taxi',
    'timeout_customer', 'timeout_taxi',
    'outdated_customer', 'outdated_taxi', 'failure',
    'accepted_by_customer')
new_options = sorted(old_options + ('declined_by_customer',))

old_type = sa.Enum(*old_options, name='status')
new_type = sa.Enum(*new_options, name='status')
tmp_type = sa.Enum(*new_options, name='_status')

tcr = sa.sql.table('hail',
                           sa.Column('status', new_type, nullable=False))
def upgrade():
    op.execute(sa.text('COMMIT'))
    op.execute(sa.text("ALTER TYPE hail_status ADD value 'declined_by_customer' after 'accepted_by_customer';"))



def downgrade():
    pass
