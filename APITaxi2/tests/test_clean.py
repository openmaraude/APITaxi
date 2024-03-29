import datetime

from APITaxi_models2 import db, Hail, Taxi, Driver, ADS, VehicleDescription
from APITaxi_models2 import Customer
from APITaxi_models2.stats import *
from APITaxi_models2.unittest import factories

from APITaxi2 import clean_db, redis_backend


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
            added_at=over_two_months,
            initial_taxi_lon=2.35,
            initial_taxi_lat=48.86,
        )
        recent_hail = factories.HailFactory(
            added_at=below_two_months,
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

        factories.HailFactory(id='old', added_at=over_a_year, blurred=True)
        factories.HailFactory(id='blurred', added_at=over_two_months, blurred=True)
        factories.HailFactory(id='recent', added_at=below_two_months)

        assert clean_db.delete_old_hails() == 1

        assert {hail.id for hail in Hail.query.all()} == {'blurred', 'recent'}


class TestComputeStatsHails:
    def test_ok(self, app):
        now = datetime.datetime.now()
        yesterday = now - datetime.timedelta(days=1)

        factories.HailFactory(
            id='yesterday',
            added_at=yesterday,
            initial_taxi_lat=48.850,
            initial_taxi_lon=2.308,
            transition_log=[
                {"from_status": None, "to_status": "received", "timestamp": yesterday.isoformat()},
            ]
        )
        factories.HailFactory(id='recent', added_at=now, transition_log=[
            {"from_status": None, "to_status": "received", "timestamp": now.isoformat()},
        ])

        assert clean_db.compute_stats_hails() == 1

        assert {hail.id for hail in Hail.query.all()} == {'yesterday', 'recent'}
        assert {hail.id for hail in StatsHails.query.all()} == {'yesterday'}
        assert int(StatsHails.query.one().hail_distance) == 89  # double checked


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

        assert clean_db.delete_old_orphans() == (1, 1, 1, 0)

        # Taxis are still complete (foreign keys would prevent deleting their relations)
        assert {t.id for t in Taxi.query.all()} == {'old_taxi', 'recent_taxi'}
        assert Driver.query.count() == 3  # The two taxis still existing
        assert ADS.query.count() == 3     # plus the too recent to be deleted orphans
        assert VehicleDescription().query.count() == 3

    def test_delete_old_customers(self, app):
        now = datetime.datetime.now()
        over_two_months = now - datetime.timedelta(days=60)
        over_a_year = now - datetime.timedelta(days=366)  # don't fail on leap years

        factories.CustomerFactory(
            id='now',
            added_at=now,
        )
        factories.CustomerFactory(
            id='over_two_months',
            added_at=over_two_months,
        )
        factories.CustomerFactory(
            id='over_a_year',
            added_at=over_a_year,
        )

        # Old account but still referenced
        factories.HailFactory(
            customer__id='over_a_year_still_referenced',
            customer__added_at=over_a_year,
        )

        assert clean_db.delete_old_orphans() == (0, 0, 0, 1)
        assert {c.id for c in Customer.query.all()} == {
            'now', 'over_two_months', 'over_a_year_still_referenced'
        }
