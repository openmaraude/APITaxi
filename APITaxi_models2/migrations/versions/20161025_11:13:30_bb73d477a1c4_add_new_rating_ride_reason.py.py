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
new_options = old_options + ['automatic_rating']

old_name = 'rating_ride_reason_enum'
tmp_name = '_' + old_name
column_name = 'rating_ride_reason'
old_type = sa.Enum(*old_options, name=old_name)
new_type = sa.Enum(*new_options, name=old_name)
tmp_type = sa.Enum(*new_options, name=tmp_name)

hail = sa.sql.table('hail',
            sa.Column(column_name, new_type, nullable=False))

def upgrade():
    tmp_type.create(op.get_bind(), checkfirst=False)
    op.execute(sa.text('ALTER TABLE hail ALTER COLUMN {column_name} TYPE {tmp_name}'
               ' USING rating_ride_reason::text::{tmp_name}'.format(
                   tmp_name=tmp_name, column_name=column_name)))
    old_type.drop(op.get_bind(), checkfirst=False)
    new_type.create(op.get_bind(), checkfirst=False)
    op.execute(sa.text('ALTER TABLE hail ALTER COLUMN {column_name} TYPE {old_name}'
               ' USING rating_ride_reason::text::{old_name}'.format(
               old_name=old_name, column_name=column_name)))
    tmp_type.drop(op.get_bind(), checkfirst=False)


def downgrade():
    op.execute(hail.update().where(hail.c.rating_ride_reason=='automatic_rating')
               .values(rating_ride_reason='ko'))
    tmp_type.create(op.get_bind(), checkfirst=False)
    op.execute(sa.text('ALTER TABLE hail ALTER COLUMN {column_name} TYPE {tmp_name}'
               ' USING rating_ride_reason::text::{tmp_name}'.format(
               column_name=column_name, tmp_name=tmp_name)))
    new_type.drop(op.get_bind(), checkfirst=False)
    old_type.create(op.get_bind(), checkfirst=False)
    op.execute(sa.text('ALTER TABLE hail ALTER COLUMN {column_name} TYPE {old_name}'
               ' USING rating_ride_reason::text::{old_name}'.format(
               column_name=column_name, old_name=old_name)))
    tmp_type.drop(op.get_bind(), checkfirst=False)
