import collections
import datetime
import itertools
import logging
import random
import time

from flask import Blueprint
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from APITaxi_models2 import db, ADS, Station, Town, Taxi, Vehicle, VehicleDescription, ZUPC

from APITaxi2 import redis_backend
from APITaxi2.views import geotaxi


blueprint = Blueprint('commands_debug_stations', __name__, cli_group=None)

logger = logging.getLogger(__name__)

now = datetime.datetime.now(datetime.timezone.utc).isoformat()


def _preload_allowed_insee():
    """A taxi from a given town is allowed in other towns of the same ZUPC."""
    allowed_insee = collections.defaultdict(list)
    # too bad we're loading the full objects for a single field
    for zupc in ZUPC.query.options(joinedload(Town, ZUPC.allowed)):
        zupc_allowed = [town.insee for town in zupc.allowed]
        for town in zupc.allowed:
            allowed_insee[town.insee].extend(zupc_allowed)

    return allowed_insee


@blueprint.cli.command('fill_stations')
def fill_stations():
    # Keep a single station per town
    stations = collections.defaultdict(list)
    for station_id, lon, lat, insee in db.session.query(
        Station.id,
        func.ST_X(func.Geometry(Station.location)),
        func.ST_Y(func.Geometry(Station.location)),
        Town.insee,
    ).join(
        Town
    ).order_by(Station.id):
        stations[insee].append((station_id, lon, lat))

    print("stations", stations.keys())

    allowed_insee = _preload_allowed_insee()

    # Move all free taxis to a station where available
    while True:
        print("Rerouting taxis to stations...", end=" ")
        t0 = time.time()
        query = db.session.query(Taxi).filter(
            # VehicleDescription.status == 'free',
        ).join(Vehicle, ADS).join(VehicleDescription).options(
            joinedload(Taxi.ads),
            joinedload(Taxi.added_by),
            joinedload(Taxi.vehicle).joinedload(Vehicle.descriptions).joinedload(VehicleDescription.added_by),
        )
        # print("query", query)
        t1 = time.time()
        results = query.all()
        t2 = time.time()
        print("query fetched in ", int(t2 - t1), end=" ")
        pipeline = redis_backend.current_app.redis.pipeline()
        for taxi in results:
            allowed = allowed_insee[taxi.ads.insee]
            subset = list(itertools.chain(*(stations[insee] for insee in allowed if insee in stations)))
            if not subset:
                continue
            station_id, lon, lat = random.choice(subset)
            # print(f"Rerouting taxi {taxi.id} to station {station_id}")
            # Bypass _update_position()
            geotaxi._update_redis(pipeline, {
                'taxi_id': taxi.id,
                'lon': lon + random.uniform(-0.0001, 0.0001),  # ~15.7 m
                'lat': lat + random.uniform(-0.0001, 0.0001),  # ~15.7 m
            }, taxi.added_by)
            # Simulate what happens when a taxi status is posted
            for vehicle_description in taxi.vehicle.descriptions:
                # Bypass set_taxi_availability()
                key = f'{taxi.id}:{vehicle_description.added_by.email}'
                if vehicle_description.status == 'free':
                    pipeline.zrem('not_available', key)
                else:
                    pipeline.zadd('not_available', {key: 0})
        t3 = time.time()
        print("taxis updated in ", int(t3 - t2), end=" ")
        pipeline.execute()
        t4 = time.time()
        print("redis updated in ", int(t4 - t3), end=" ")

        print("done in", int(t4 - t0))
        time.sleep(30)
