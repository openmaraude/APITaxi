"""update rating and reporting reasons

Revision ID: 30bcf72d7430
Revises: 4d09adff27fb
Create Date: 2015-12-08 13:09:19.160565

"""

# revision identifiers, used by Alembic.
revision = '30bcf72d7430'
down_revision = '4d09adff27fb'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

old_rating_ride_reason_enum = sa.Enum('late', 'no_credit_card', 'bad_itinerary', 'dirty_taxi',
        name='rating_ride_reason_enum')
tmp_rating_ride_reason_enum = sa.Enum('ko', 'payment', 'courtesy', 'route',
        'cleanliness', 'late', 'no_credit_card', 'bad_itinerary', 'dirty_taxi',
        name='_rating_ride_reason_enum')
new_rating_ride_reason_enum = sa.Enum('ko', 'payment', 'courtesy', 'route',
        'cleanliness', 'late', 'no_credit_card', 'bad_itinerary', 'dirty_taxi',
        name='rating_ride_reason_enum')

old_reporting_customer_reason_enum = sa.Enum('late', 'aggressive', 'no_show',
        name='reporting_customer_reason_enum')
tmp_reporting_customer_reason_enum = sa.Enum('ko', 'payment', 'courtesy', 'route',
        'cleanliness', 'late', 'aggressive', 'no_show',
        name='_reporting_customer_reason_enum')
new_reporting_customer_reason_enum = sa.Enum('ko', 'payment', 'courtesy', 'route',
        'cleanliness', 'late', 'aggressive', 'no_show',
        name='reporting_customer_reason_enum')

old_incident_taxi_reason_enum = sa.Enum('traffic_jam', 'garbage_truck',
        name='incident_taxi_reason_enum')
tmp_incident_taxi_reason_enum = sa.Enum('no_show', 'address', 'traffic', 'breakdown',
        'traffic_jam', 'garbage_truck',
        name='_incident_taxi_reason_enum')
new_incident_taxi_reason_enum = sa.Enum('no_show', 'address', 'traffic', 'breakdown',
        'traffic_jam', 'garbage_truck',
        name='incident_taxi_reason_enum')

old_incident_customer_reason_enum = sa.Enum('mud_river', 'parade', 'earthquake',
        name='incident_customer_reason_enum')
tmp_incident_customer_reason_enum = sa.Enum('',
        'mud_river', 'parade', 'earthquake',
        name='_incident_customer_reason_enum')
new_incident_customer_reason_enum = sa.Enum('',
        'mud_river', 'parade', 'earthquake',
        'no_show', 'no_specs',
        name='incident_customer_reason_enum')

hail = sa.sql.table('hail',
        sa.Column('rating_ride_reason', new_rating_ride_reason_enum, nullable=True),
        sa.Column('reporting_customer_reason', new_reporting_customer_reason_enum, nullable=True),
        sa.Column('incident_taxi_reason', new_incident_taxi_reason_enum, nullable=True),
        sa.Column('incident_customer_reason', new_incident_customer_reason_enum, nullable=True),
        )


def upgrade():

    tmp_rating_ride_reason_enum.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN rating_ride_reason TYPE _rating_ride_reason_enum'
                           ' USING rating_ride_reason::text::_rating_ride_reason_enum')
    old_rating_ride_reason_enum.drop(op.get_bind(), checkfirst=False)
    new_rating_ride_reason_enum.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN rating_ride_reason TYPE rating_ride_reason_enum'
                           ' USING rating_ride_reason::text::rating_ride_reason_enum')
    tmp_rating_ride_reason_enum.drop(op.get_bind(), checkfirst=False)

    op.execute(hail.update().where(hail.c.rating_ride_reason=='no_credit_card')
                .values(rating_ride_reason='payment'))
    op.execute(hail.update().where(hail.c.rating_ride_reason=='bad_itinerary')
                 .values(rating_ride_reason='route'))
    op.execute(hail.update().where(hail.c.rating_ride_reason=='dirty_taxi')
                 .values(rating_ride_reason='cleanliness'))
    op.execute(hail.update().where(hail.c.rating_ride_reason=='late')
                 .values(rating_ride_reason='route'))


    tmp_reporting_customer_reason_enum.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN reporting_customer_reason TYPE _reporting_customer_reason_enum'
                           ' USING reporting_customer_reason::text::_reporting_customer_reason_enum')
    old_reporting_customer_reason_enum.drop(op.get_bind(), checkfirst=False)
    new_reporting_customer_reason_enum.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN reporting_customer_reason TYPE reporting_customer_reason_enum'
                           ' USING reporting_customer_reason::text::reporting_customer_reason_enum')
    tmp_reporting_customer_reason_enum.drop(op.get_bind(), checkfirst=False)

    op.execute(hail.update().where(hail.c.reporting_customer_reason=='late')
                 .values(reporting_customer_reason='route'))
    op.execute(hail.update().where(hail.c.reporting_customer_reason=='aggressive')
                  .values(reporting_customer_reason='courtesy'))
    op.execute(hail.update().where(hail.c.reporting_customer_reason=='no_show')
                  .values(reporting_customer_reason='ko'))


    tmp_incident_taxi_reason_enum.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN incident_taxi_reason TYPE _incident_taxi_reason_enum'
                           ' USING incident_taxi_reason::text::_incident_taxi_reason_enum')
    old_incident_taxi_reason_enum.drop(op.get_bind(), checkfirst=False)
    new_incident_taxi_reason_enum.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN incident_taxi_reason TYPE incident_taxi_reason_enum'
                          ' USING incident_taxi_reason::text::incident_taxi_reason_enum')
    tmp_incident_taxi_reason_enum.drop(op.get_bind(), checkfirst=False)

    op.execute(hail.update().where(hail.c.incident_taxi_reason=='traffic_jam')
                  .values(incident_taxi_reason='traffic'))
    op.execute(hail.update().where(hail.c.incident_taxi_reason=='garbage_truck')
                   .values(incident_taxi_reason='traffic'))


    tmp_incident_customer_reason_enum.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN incident_customer_reason TYPE _incident_customer_reason_enum'
                           ' USING incident_customer_reason::text::_incident_customer_reason_enum')
    old_incident_customer_reason_enum.drop(op.get_bind(), checkfirst=False)
    new_incident_customer_reason_enum.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN incident_customer_reason TYPE incident_customer_reason_enum'
                           ' USING incident_customer_reason::text::incident_customer_reason_enum')
    tmp_incident_customer_reason_enum.drop(op.get_bind(), checkfirst=False)

    op.execute(hail.update().where(hail.c.incident_customer_reason=='mud_river')
                  .values(incident_customer_reason=''))
    op.execute(hail.update().where(hail.c.incident_customer_reason=='parade')
                  .values(incident_customer_reason=''))
    op.execute(hail.update().where(hail.c.incident_customer_reason=='earthquake')
                  .values(incident_customer_reason=''))


def downgrade():
    op.execute(hail.update().where(hail.c.rating_ride_reason=='payment')
                 .values(rating_ride_reason='no_credit_card'))
    op.execute(hail.update().where(hail.c.rating_ride_reason=='route')
                 .values(rating_ride_reason='bad_itinerary'))
    op.execute(hail.update().where(hail.c.rating_ride_reason=='cleanliness')
                 .values(rating_ride_reason='dirty_taxi'))
    op.execute(hail.update().where(hail.c.rating_ride_reason=='courtesy')
                 .values(rating_ride_reason='dirty_taxi'))
    op.execute(hail.update().where(hail.c.rating_ride_reason=='ko')
                 .values(rating_ride_reason='dirty_taxi'))

    tmp_rating_ride_reason_enum.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN rating_ride_reason TYPE _rating_ride_reason_enum'
               ' USING rating_ride_reason::text::_rating_ride_reason_enum');
    new_rating_ride_reason_enum.drop(op.get_bind(), checkfirst=False)
    old_rating_ride_reason_enum.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN rating_ride_reason TYPE rating_ride_reason_enum'
               ' USING rating_ride_reason::text::rating_ride_reason_enum');
    tmp_rating_ride_reason_enum.drop(op.get_bind(), checkfirst=False)


    op.execute(hail.update().where(hail.c.reporting_customer_reason=='route')
                  .values(reporting_customer_reason='late'))
    op.execute(hail.update().where(hail.c.reporting_customer_reason=='courtesy')
                  .values(reporting_customer_reason='aggressive'))
    op.execute(hail.update().where(hail.c.reporting_customer_reason=='cleanliness')
                  .values(reporting_customer_reason='late'))
    op.execute(hail.update().where(hail.c.reporting_customer_reason=='payment')
                  .values(reporting_customer_reason='no_show'))
    op.execute(hail.update().where(hail.c.reporting_customer_reason=='ko')
                  .values(reporting_customer_reason='no_show'))

    tmp_reporting_customer_reason_enum.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN reporting_customer_reason TYPE _reporting_customer_reason_enum'
               ' USING reporting_customer_reason::text::_reporting_customer_reason_enum');
    new_reporting_customer_reason_enum.drop(op.get_bind(), checkfirst=False)
    old_reporting_customer_reason_enum.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN reporting_customer_reason TYPE reporting_customer_reason_enum'
               ' USING reporting_customer_reason::text::reporting_customer_reason_enum');
    tmp_reporting_customer_reason_enum.drop(op.get_bind(), checkfirst=False)


    op.execute(hail.update().where(hail.c.incident_taxi_reason=='traffic')
                   .values(incident_taxi_reason='traffic_jam'))
    op.execute(hail.update().where(hail.c.incident_taxi_reason=='address')
                    .values(incident_taxi_reason='traffic_jam'))
    op.execute(hail.update().where(hail.c.incident_taxi_reason=='breakdown')
                    .values(incident_taxi_reason='traffic_jam'))
    op.execute(hail.update().where(hail.c.incident_taxi_reason=='no_show')
                    .values(incident_taxi_reason='traffic_jam'))

    tmp_incident_taxi_reason_enum.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN incident_taxi_reason TYPE _incident_taxi_reason_enum'
               ' USING incident_taxi_reason::text::_incident_taxi_reason_enum');
    new_incident_taxi_reason_enum.drop(op.get_bind(), checkfirst=False)
    old_incident_taxi_reason_enum.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN incident_taxi_reason TYPE incident_taxi_reason_enum'
               ' USING incident_taxi_reason::text::incident_taxi_reason_enum');
    tmp_incident_taxi_reason_enum.drop(op.get_bind(), checkfirst=False)


    op.execute(hail.update().where(hail.c.incident_customer_reason=='')
                   .values(incident_customer_reason='mud_river'))

    tmp_incident_customer_reason_enum.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN incident_customer_reason TYPE _incident_customer_reason_enum'
               ' USING incident_customer_reason::text::_incident_customer_reason_enum');
    new_incident_customer_reason_enum.drop(op.get_bind(), checkfirst=False)
    old_incident_customer_reason_enum.create(op.get_bind(), checkfirst=False)
    op.execute('ALTER TABLE hail ALTER COLUMN incident_customer_reason TYPE incident_customer_reason_enum'
               ' USING incident_customer_reason::text::incident_customer_reason_enum');
    tmp_incident_customer_reason_enum.drop(op.get_bind(), checkfirst=False)

