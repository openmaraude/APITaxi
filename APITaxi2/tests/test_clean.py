import datetime

from APITaxi_models2 import db, Hail, ArchivedHail, Taxi, Driver, ADS, VehicleDescription
from APITaxi_models2.stats import *
from APITaxi_models2.unittest import factories

from APITaxi2 import clean_db, redis_backend


class TestTownHelper:
    def test_ok(self, app, QueriesTracker):
        factories.TownFactory(bordeaux=True)
        factories.TownFactory(charenton=True)
        factories.TownFactory(paris=True)

        with QueriesTracker() as qtracker:
            town_helper = clean_db.TownHelper()
            assert qtracker.count == 1

        insee = town_helper.find_town(2.35, 48.86)
        assert insee == '75056'
        insee = town_helper.find_town(-0.57847, 44.8434)
        assert insee == '33063'

        zero = town_helper.find_town(0, 0)
        assert zero is None
        not_found = town_helper.find_town(48.86, 2.35)  # Inverted lon/lat
        assert not_found is None


class TestBlurGeoTaxi:
    def test_ok(self, app):
        now = datetime.datetime.now()
        over_two_months = now - datetime.timedelta(days=60)
        below_two_months = now - datetime.timedelta(days=59)

        # Old location
        app.redis.hset(
            'taxi:taxi1',
            "taxis_bleus",
            '%s 48.86 2.35 free phone 2' % int(over_two_months.timestamp())
        )

        # Location still preserved
        app.redis.hset(
            'taxi:taxi2',
            'taxis_verts',
            '%s 48.86 2.35 free phone 2' % int(below_two_months.timestamp())
        )

        assert clean_db.blur_geotaxi() == 1

        taxi1 = redis_backend.get_taxi('taxi1', 'taxis_bleus')
        assert (taxi1.lon, taxi1.lat) == (0.0, 0.0)
        taxi2 = redis_backend.get_taxi('taxi2', 'taxis_verts')
        assert (taxi2.lon, taxi2.lat) == (2.35, 48.86)


class TestBlurHails:
    def test_ok(self, app):
        now = datetime.datetime.now()
        over_two_months = now - datetime.timedelta(days=60)
        below_two_months = now - datetime.timedelta(days=59)

        old_hail = factories.HailFactory(
            creation_datetime=over_two_months,
            initial_taxi_lon=2.35,
            initial_taxi_lat=48.86,
        )
        recent_hail = factories.HailFactory(
            creation_datetime=below_two_months,
            # Bordeaux
            customer_lon=-0.57847,
            customer_lat=44.8434,
            initial_taxi_lon=-0.57752,
            initial_taxi_lat=44.84277,
        )
        factories.TownFactory(bordeaux=True)
        factories.TownFactory(charenton=True)
        factories.TownFactory(paris=True)

        assert clean_db.blur_hails() == 1

        # Representative point of the factory bbox
        assert (old_hail.customer_lon, old_hail.customer_lat) == (2.3339645305841, 48.8594281662316)
        assert (old_hail.initial_taxi_lon, old_hail.initial_taxi_lat) == (2.3339645305841, 48.8594281662316)
        assert old_hail.customer_address == old_hail.customer_phone_number == old_hail.taxi_phone_number == "[REDACTED]"
        assert old_hail.blurred is True
        # Factory original value
        assert (recent_hail.customer_lon, recent_hail.customer_lat) == (-0.57847, 44.8434)
        assert (recent_hail.initial_taxi_lon, recent_hail.initial_taxi_lat) == (-0.57752, 44.84277)
        assert recent_hail.blurred is False


class TestArchiveHails:
    def test_ok(self, app):
        now = datetime.datetime.now()
        over_a_year = now - datetime.timedelta(days=366)  # don't fail on leap years
        over_two_months = now - datetime.timedelta(days=60)
        below_two_months = now - datetime.timedelta(days=59)

        factories.HailFactory(id='old', creation_datetime=over_a_year, blurred=True)
        factories.HailFactory(id='blurred', creation_datetime=over_two_months, blurred=True)
        factories.HailFactory(id='recent', creation_datetime=below_two_months)

        assert clean_db.archive_hails() == 1

        assert {hail.id for hail in Hail.query.all()} == {'blurred', 'recent'}
        assert {hail.id for hail in ArchivedHail().query.all()} == {'old'}


class TestDeleteOldTaxis:
    def test_ok(self, app):
        now = datetime.datetime.now()
        over_a_year = now - datetime.timedelta(days=366)  # don't fail on leap years
        over_two_months = now - datetime.timedelta(days=60)

        # Old and never pushed to Redis
        factories.TaxiFactory(id='old_not_in_redis', added_at=over_a_year)
        # Old and orphan, as in never hailed
        old_orphan_taxi = factories.TaxiFactory(id='old_orphan', added_at=over_a_year)
        app.redis.hset(
            'taxi:old_orphan',
            f"{old_orphan_taxi.added_by.email}",
            '%s 48.86 2.35 free phone 2' % int(over_a_year.timestamp())
        )
        # Old and orphan, but still active
        old_active_taxi = factories.TaxiFactory(id='old_active', added_at=over_a_year)
        app.redis.hset(
            'taxi:old_active',
            f"{old_active_taxi.added_by.email}",
            '%s 48.86 2.35 free phone 2' % int(now.timestamp())
        )
        # Old taxi referenced in a hail
        old_hailed_taxi = factories.HailFactory(taxi__id='old_hailed', taxi__added_at=over_a_year).taxi
        app.redis.hset(
            'taxi:old_hailed',
            f"{old_hailed_taxi.added_by.email}",
            '%s 48.86 2.35 free phone 2' % int(over_a_year.timestamp())
        )
        # Recent and not hailed yet
        recent_orphan_taxi = factories.TaxiFactory(id='recent_orphan', added_at=over_two_months)
        app.redis.hset(
            'taxi:recent_orphan',
            f"{recent_orphan_taxi.added_by.email}",
            '%s 48.86 2.35 free phone 2' % int(over_two_months.timestamp())
        )
        # Recent and hailed
        recent_hailed_taxi = factories.HailFactory(taxi__id='recent_hailed', taxi__added_at=over_two_months).taxi
        app.redis.hset(
            'taxi:recent_hailed',
            f"{recent_hailed_taxi.added_by.email}",
            '%s 48.86 2.35 free phone 2' % int(over_two_months.timestamp())
        )
        # Recent but still not in Redis
        factories.Taxi(id='recent_not_in_redis', added_at=over_two_months)
        # And this one was made up
        app.redis.hset(
            'taxi:foobar',
            "taxis_bleus",
            '%s 48.86 2.35 free phone 2' % int(over_a_year.timestamp())
        )

        # old_not_in_redis and old_orphan_taxi deleted
        assert clean_db.delete_old_taxis() == 2

        taxi_ids = {t.id for t in Taxi.query.all()}
        assert taxi_ids == {'old_active', 'old_hailed', 'recent_orphan', 'recent_hailed'}

        # Redis only contains taxis still existing
        taxi_ids = {u.taxi_id for u in redis_backend.list_taxis(0, now.timestamp())}
        assert taxi_ids == {'old_active', 'old_hailed', 'recent_orphan', 'recent_hailed'}


class TestDeleteOldOrphans:
    def test_ok(self, app):
        now = datetime.datetime.now()
        over_a_year = now - datetime.timedelta(days=366)  # don't fail on leap years
        over_two_months = now - datetime.timedelta(days=60)

        factories.TaxiFactory(
            id='old_taxi',
            added_at=over_a_year,
            driver__added_at=over_a_year,
            ads__added_at=over_a_year,
            vehicle__descriptions__added_at=over_a_year,
        )
        factories.TaxiFactory(
            id='deleted_old_taxi',
            added_at=over_a_year,
            driver__added_at=over_a_year,
            ads__added_at=over_a_year,
            vehicle__descriptions__added_at=over_a_year,
        )
        Taxi.query.filter_by(id='deleted_old_taxi').delete()
        factories.TaxiFactory(
            id='recent_taxi',
            added_at=over_two_months,
            driver__added_at=over_two_months,
            ads__added_at=over_two_months,
            vehicle__descriptions__added_at=over_two_months,
        )
        factories.DriverFactory(added_at=over_two_months)  # Recent orphans
        factories.ADSFactory(added_at=over_two_months)
        factories.VehicleDescription(added_at=over_two_months)

        assert clean_db.delete_old_orphans() == (1, 1, 1)

        # Taxis are still complete (foreign keys would prevent deleting their relations)
        assert {t.id for t in Taxi.query.all()} == {'old_taxi', 'recent_taxi'}
        assert Driver.query.count() == 3  # The two taxis still existing
        assert ADS.query.count() == 3     # plus the too recent to be deleted orphans
        assert VehicleDescription().query.count() == 3


class TestDeleteOldStats:
    def test_ok(self, app):
        now = datetime.datetime.now()
        old = now - datetime.timedelta(days=8)
        recent = now - datetime.timedelta(days=6)

        db.session.add(stats_minute(time=old, value=10))
        db.session.add(stats_minute(time=recent, value=20))

        assert stats_minute.query.count() == 2
        clean_db.delete_old_stats_minute()
        assert stats_minute.query.count() == 1
