import datetime
import functools

from flask import current_app
from geoalchemy2.shape import to_shape
from shapely.geometry import Point
from shapely.strtree import STRtree
from sqlalchemy import func, Text
from sqlalchemy.orm import aliased, joinedload
from sqlalchemy.dialects.postgresql import JSONB, INTERVAL

from APITaxi2 import redis_backend
from APITaxi_models2 import db, ADS, ArchivedHail, Driver, Taxi, VehicleDescription, Hail, Town, User
from APITaxi_models2 import Customer
from APITaxi_models2.zupc import town_zupc
from APITaxi_models2.stats import *


class TownHelper:

    def __init__(self, insee_codes):
        self._shape_to_insee = {}
        self._insee_to_shape = {}
        self._preload_towns(insee_codes)

    def _preload_towns(self, insee_codes):
        for town in db.session.query(Town).filter(Town.insee.in_(insee_codes)):
            shape = to_shape(town.shape)
            self._shape_to_insee[id(shape)] = town.insee  # MultiPolygon unhashable
            self._insee_to_shape[town.insee] = shape
        # Build an index of geometries
        self._tree = STRtree(self._insee_to_shape.values())

    def find_town(self, lon, lat):
        if lon == 0.0 and lat == 0.0:  # Seen in production
            return None
        point = Point(lon, lat)
        for shape in self._tree.query(point):
            if not shape.contains(point):  # See STRtree docs
                continue
            return self._shape_to_insee[id(shape)]
        return None

    @functools.lru_cache()
    def geometric_center(self, insee):
        if insee is None:
            return Point(0, 0)
        # Quoting the documentation:
        #   Returns a cheaply computed point that is guaranteed to be within the geometric object.
        # whereas the centroid provides neither of these
        return self._insee_to_shape[insee].representative_point()


def blur_geotaxi():
    """
    There is a celery task already deleting geolocation after two minutes, except for the
    main index, used for statistics.

    We need to expire this index after two months, but we also need it for later detecting inactive
    taxis (delete_old_taxis). Instead, replace the locations with null data.
    """
    threshold = datetime.datetime.now() - datetime.timedelta(days=60)
    pipeline = current_app.redis.pipeline()
    count = 0

    for count, update in enumerate(redis_backend.list_taxis(0, threshold.timestamp()), 1):
        # Same structure and data as geotaxi, just zeroing the location
        pipeline.hset(
            f"taxi:{update.taxi_id}",
            update.operator,
            f"{update.timestamp} 0.0 0.0 free phone 2",
        )

    pipeline.execute()
    return count


def blur_hails():
    """
    After two months, location is blurred to only point to the geographical center of the town.

    Blurred hails are tagged, so we know the location is approximated.
    """
    threshold = datetime.datetime.now() - datetime.timedelta(days=60)

    # First preload the subset of towns we'll work with. We can't tell which towns we'll need in advance
    # but we can already limit to towns where taxis are registered.
    ads_insee = {insee for insee, in db.session.query(ADS.insee)}
    zupc_insee = {insee for insee, in db.session.query(Town.insee).join(town_zupc)}
    town_helper = TownHelper(ads_insee | zupc_insee)

    count = 0

    for count, hail in enumerate(db.session.query(Hail).filter(
        Hail.added_at < threshold,
        Hail.blurred.is_(False),
        # Finding a way to order by position, to optimize the LRU cache?
    ), 1):
        # Blur customer position
        insee = town_helper.find_town(hail.customer_lon, hail.customer_lat)
        blurred = town_helper.geometric_center(insee)
        hail.customer_lon, hail.customer_lat = blurred.x, blurred.y
        # Blur taxi position
        if hail.initial_taxi_lon and hail.initial_taxi_lat:
            insee = town_helper.find_town(hail.initial_taxi_lon, hail.initial_taxi_lat)
            blurred = town_helper.geometric_center(insee)
            hail.initial_taxi_lon, hail.initial_taxi_lat = blurred.x, blurred.y
        # Blur text-plain address
        hail.customer_address = "[REDACTED]"
        # Blur phone numbers
        hail.customer_phone_number = "[REDACTED]"
        hail.taxi_phone_number = "[REDACTED]"
        hail.blurred = True
        db.session.add(hail)

    db.session.commit()
    return count


def compute_stats_hails():
    """
    Extract what we need to build stats, then the hails can be deleted after they expire.
    """
    count = 0
    last_run = db.session.query(func.max(StatsHails.added_at)).scalar() or datetime.datetime.fromtimestamp(0)
    Operateur = aliased(User)
    Moteur = aliased(User)
    query = db.session.query(
        Hail,
        Town.insee,
        func.encode(func.digest(Hail.taxi_id, 'sha1'), 'hex').label('taxi_hash'),
        Moteur.email,
        Operateur.email,
        # JSONB cannot be cast to a timestamp field, but TEXT can
        func.jsonb_path_query(Hail.transition_log.cast(JSONB()), '$[*] ? (@.to_status == $status).timestamp', '{"status": "received"}').cast(Text()).label('received'),
        func.jsonb_path_query(Hail.transition_log.cast(JSONB()), '$[*] ? (@.to_status == $status).timestamp', '{"status": "sent_to_operator"}').cast(Text()).label('sent_to_operator'),
        func.jsonb_path_query(Hail.transition_log.cast(JSONB()), '$[*] ? (@.to_status == $status).timestamp', '{"status": "received_by_operator"}').cast(Text()).label('received_by_operator'),
        func.jsonb_path_query(Hail.transition_log.cast(JSONB()), '$[*] ? (@.to_status == $status).timestamp', '{"status": "received_by_taxi"}').cast(Text()).label('received_by_taxi'),
        func.jsonb_path_query(Hail.transition_log.cast(JSONB()), '$[*] ? (@.to_status == $status).timestamp', '{"status": "accepted_by_taxi"}').cast(Text()).label('accepted_by_taxi'),
        func.jsonb_path_query(Hail.transition_log.cast(JSONB()), '$[*] ? (@.to_status == $status).timestamp', '{"status": "accepted_by_customer"}').cast(Text()).label('accepted_by_customer'),
        func.jsonb_path_query(Hail.transition_log.cast(JSONB()), '$[*] ? (@.to_status == $status).timestamp', '{"status": "declined_by_taxi"}').cast(Text()).label('declined_by_taxi'),
        func.jsonb_path_query(Hail.transition_log.cast(JSONB()), '$[*] ? (@.to_status == $status).timestamp', '{"status": "declined_by_customer"}').cast(Text()).label('declined_by_customer'),
        func.jsonb_path_query(Hail.transition_log.cast(JSONB()), '$[*] ? (@.to_status == $status).timestamp', '{"status": "timeout_taxi"}').cast(Text()).label('timeout_taxi'),
        func.jsonb_path_query(Hail.transition_log.cast(JSONB()), '$[*] ? (@.to_status == $status).timestamp', '{"status": "timeout_customer"}').cast(Text()).label('timeout_customer'),
        func.jsonb_path_query(Hail.transition_log.cast(JSONB()), '$[*] ? (@.to_status == $status).timestamp', '{"status": "incident_taxi"}').cast(Text()).label('incident_taxi'),
        func.jsonb_path_query(Hail.transition_log.cast(JSONB()), '$[*] ? (@.to_status == $status).timestamp', '{"status": "incident_customer"}').cast(Text()).label('incident_customer'),
        func.jsonb_path_query(Hail.transition_log.cast(JSONB()), '$[*] ? (@.to_status == $status).timestamp', '{"status": "customer_on_board"}').cast(Text()).label('customer_on_board'),
        func.jsonb_path_query(Hail.transition_log.cast(JSONB()), '$[*] ? (@.to_status == $status).timestamp', '{"status": "finished"}').cast(Text()).label('finished'),
        func.jsonb_path_query(Hail.transition_log.cast(JSONB()), '$[*] ? (@.to_status == $status).timestamp', '{"status": "failure"}').cast(Text()).label('failure'),
    ).join(
        Moteur, Hail.added_by_id == Moteur.id
    ).join(
        Operateur, Hail.operateur_id == Operateur.id
    ).outerjoin(
        Town, func.st_intersects(Town.shape, func.st_point(Hail.customer_lon, Hail.customer_lat, 4326)),
    ).filter(
        Hail.added_at > last_run,
        Hail.added_at < func.now() - func.cast('24 hours', INTERVAL()),
    )

    for count, (hail, insee, taxi_hash, moteur, operateur, *timings) in enumerate(query, 1):
        stats_hail = StatsHails(
            added_at=hail.added_at,
            added_via=hail.added_via,
            source=hail.source,
            last_update_at=hail.last_update_at,
            id=hail.id,
            status=hail.status,
            moteur=moteur,
            operateur=operateur,
            incident_customer_reason=hail.incident_customer_reason,
            incident_taxi_reason=hail.incident_taxi_reason,
            session_id=hail.session_id,
            reporting_customer=hail.reporting_customer,
            reporting_customer_reason=hail.reporting_customer_reason,
            insee=insee,
            taxi_hash=taxi_hash,
            received=timings[0],
            sent_to_operator=timings[1],
            received_by_operator=timings[2],
            received_by_taxi=timings[3],
            accepted_by_taxi=timings[4],
            accepted_by_customer=timings[5],
            declined_by_taxi=timings[6],
            declined_by_customer=timings[7],
            timeout_taxi=timings[8],
            timeout_customer=timings[9],
            incident_taxi=timings[10],
            incident_customer=timings[11],
            customer_on_board=timings[12],
            finished=timings[13],
            failure=timings[14],
        )
        db.session.add(stats_hail)

    db.session.commit()
    return count


# TODO remove after transition
def compute_archived_hails():
    count = 0
    query = db.session.query(ArchivedHail)

    for count, archived_hail in enumerate(query, 1):
        stats_hail = StatsHails(
            added_at=archived_hail.added_at,
            added_via=archived_hail.added_via,
            source=archived_hail.source,
            last_update_at=archived_hail.last_update_at,
            id=archived_hail.id,
            status=archived_hail.status,
            moteur=archived_hail.moteur,
            operateur=archived_hail.operateur,
            incident_customer_reason=archived_hail.incident_customer_reason,
            incident_taxi_reason=archived_hail.incident_taxi_reason,
            session_id=archived_hail.session_id,
            insee=archived_hail.insee,

        )
        db.session.add(stats_hail)

    db.session.commit()
    return count


def delete_old_hails():
    """
    After a year, blurred hails are deleted. We already saved what is needed for stats.
    """
    hail_ids = [
        hail_id for hail_id, in db.session.query(Hail.id).filter(
            Hail.added_at < func.now() - func.cast('1 year', INTERVAL()),
            Hail.blurred.is_(True),
        )
    ]

    # Cut reference to foreign key, so we can delete them
    db.session.query(Taxi).filter(Taxi.current_hail_id.in_(hail_ids)).update({
        Taxi.current_hail_id: None
    })

    db.session.query(Hail).filter(Hail.id.in_(hail_ids)).delete()
    db.session.commit()
    return len(hail_ids)


def delete_old_taxis():
    """
    If a taxi hasn't sent a location after a year, it can be deleted. Geolocation indices are deleted
    after two minutes, but we keep a reference in the main index, preserved by blur_geotaxi above.

    As a taxi can be related to a hail, the latter must be deleted before we can delete the taxi.

    Then we can delete now orphaned drivers, vehicles and ADS over a year old in the function below.
    """
    threshold = datetime.datetime.now() - datetime.timedelta(days=365)

    # As taxis and hails are related, we can't delete a taxi before the last hail
    # referencing it was deleted
    old_taxis_still_referenced = {
        taxi_id for taxi_id, in db.session.query(Hail.taxi_id).join(Hail.taxi).filter(
            Taxi.added_at < threshold,
        )
    }
    old_taxi_ids = {
        taxi_id for taxi_id, in db.session.query(Taxi.id).filter(
            Taxi.added_at < threshold,
            Taxi.id.notin_(old_taxis_still_referenced)
        )
    }
    # Confirmation from Redis of taxis not updated for over a year
    old_redis_ids = {
        update.taxi_id for update in redis_backend.list_taxis(0, threshold.timestamp())
    }
    all_redis_ids = set(redis_backend.list_taxi_ids())
    # Taxis confirmed by Redis to be not updated for over a year, plus taxis unknown
    candidates = (old_taxi_ids & old_redis_ids) | (old_taxi_ids - all_redis_ids)

    # Delete taxis for good
    count = db.session.query(Taxi).filter(Taxi.id.in_(candidates)).delete(synchronize_session=False)
    db.session.commit()

    # Then delete them in Redis
    pipeline = current_app.redis.pipeline()
    for taxi_id in candidates:
        pipeline.delete(f"taxi:{taxi_id}")

    # Delete orphan taxis dandling in Redis
    all_taxis_ids = {taxi_id for taxi_id, in db.session.query(Taxi.id)}
    orphan_ids = old_redis_ids - candidates - all_taxis_ids
    for orphan_id in orphan_ids:
        pipeline.delete(f"taxi:{orphan_id}")

    pipeline.execute()
    return count


def delete_old_orphans():
    threshold = datetime.datetime.now() - datetime.timedelta(days=365)

    def _delete_old_orphans(Model, query):
        """stripped down version of check_orphans"""
        count = db.session.query(Model).filter(
            # Can't directly call query.delete() because of the outerjoin
            Model.id.in_(id_ for id_, in query)
        ).delete(
            synchronize_session=False
        )
        db.session.commit()
        return count

    driver_count = _delete_old_orphans(
        Driver,
        db.session.query(Driver.id).outerjoin(Taxi).filter(Taxi.id.is_(None), Driver.added_at < threshold),
    )

    ads_count = _delete_old_orphans(
        ADS,
        db.session.query(ADS.id).outerjoin(Taxi).filter(Taxi.id.is_(None), ADS.added_at < threshold),
    )

    vehicle_count = _delete_old_orphans(
        VehicleDescription,
        db.session.query(VehicleDescription.id).outerjoin(
            Taxi, VehicleDescription.vehicle_id == Taxi.vehicle_id
        ).filter(
            Taxi.id.is_(None), VehicleDescription.added_at < threshold,
        ),
    )

    # Vehicles have no "added_at"

    customer_count = _delete_old_orphans(
        Customer,
        db.session.query(Customer.id).outerjoin(
            Hail, Customer.id == Hail.customer_id
        ).filter(
            Hail.id.is_(None), Customer.added_at < threshold,
        )
    )

    return driver_count, ads_count, vehicle_count, customer_count
