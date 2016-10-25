"""Add new rating_ride_reason

Revision ID: bb73d477a1c4
Revises: 986de51c9c9f
Create Date: 2016-10-25 11:13:30.478311

"""

# revision identifiers, used by Alembic.
revision = 'bb73d477a1c4'
down_revision = '986de51c9c9f'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

old_options = ['ko', 'payment', 'courtesy', 'route', 'cleanliness',
	       'late', 'no_credit_card', 'bad_itinerary', 'dirty_taxi']
new_options = old_options + ['manage_penalty_taxi']

old_type = sa.Enum(*old_options, name='rating_ride_reason_enum')
new_type = sa.Enum(*new_options, name='rating_ride_reason_enum')
tmp_type = sa.Enum(*new_options, name='_rating_ride_reason_enum')

hail = sa.sql.table('hail',
            sa.Column('rating_ride_reason', new_type, nullable=False))

def upgrade():
    tmp_type.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN rating_ride_reason TYPE _rating_ride_reason_enum'
               ' USING rating_ride_reason::text::_rating_ride_reason_enum');
    old_type.drop(op.get_bind(), checkfirst=False)
    new_type.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN rating_ride_reason TYPE rating_ride_reason_enum'
               ' USING rating_ride_reason::text::rating_ride_reason_enum');
    tmp_type.drop(op.get_bind(), checkfirst=False)


def downgrade():
    op.execute(hail.update().where(hail.c.status==u'manage_penalty_taxi')
               .values(status='ko'))
    tmp_type.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN rating_ride_reason TYPE _rating_ride_reason_enm'
               ' USING rating_ride_reason::text::_rating_ride_reason_enum');
    new_type.drop(op.get_bind(), checkfirst=False)
    old_type.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN rating_ride_reason TYPE _rating_ride_reason_enum'
               ' USING rating_ride_reason::text::rating_ride_reason_enum');
    tmp_type.drop(op.get_bind(), checkfirst=False)
