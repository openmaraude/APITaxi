"""Add accepted_by_customer

Revision ID: 3183d344740d
Revises: 4190b0aefe23
Create Date: 2015-06-30 15:00:54.718273

"""

# revision identifiers, used by Alembic.
revision = '3183d344740d'
down_revision = '4190b0aefe23'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

old_options = ( 'emitted', 'received',
    'sent_to_operator', 'received_by_operator',
    'received_by_taxi',
    'accepted_by_taxi',
    'declined_by_taxi', 'declined_by_customer',
    'incident_customer', 'incident_taxi',
    'timeout_customer', 'timeout_taxi',
    'outdated_customer', 'outdated_taxi', 'failure')
new_options = sorted(old_options + ('accepted_by_customer',))

old_type = sa.Enum(*old_options, name='status')
new_type = sa.Enum(*new_options, name='status')
tmp_type = sa.Enum(*new_options, name='_status')

tcr = sa.sql.table('hail',
                           sa.Column('status', new_type, nullable=False))
def upgrade():
    op.execute(sa.text('COMMIT'))
    op.execute(sa.text("ALTER TYPE hail_status ADD value 'accepted_by_customer' after 'accepted_by_taxi';"))


def downgrade():
    pass
