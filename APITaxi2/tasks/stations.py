import collections
from dataclasses import dataclass
import operator
import time

from flask import current_app
from geoalchemy2.shape import to_shape
from geopy.distance import geodesic, great_circle
from shapely.geometry import Point
from sqlalchemy.orm import joinedload

from APITaxi2 import redis_backend
from APITaxi_models2 import db, ADS, Station, Taxi, Town, ZUPC
from . import celery


# The precision in meters to consider a taxi is halted
TAXI_DISTANCE_JITTER = 20
# The lifetime in seconds of the station computation
STATION_DATA_TIMEOUT = 120
# GEODESIC is the most precise but the slowest
USE_GEODESIC = True


@dataclass
class StationData:
    """Represent taxis around and in stations."""
    timestamp: int
    station_id: str
    lat: float
    lon: float

    @classmethod
    def from_redis(cls, res):
        if not res:
            return None
        return cls(
            timestamp=int(res[b'timestamp']),
            station_id=res[b'station_id'].decode('utf-8'),
            lat=float(res[b'lat']),
            lon=float(res[b'lon']),
        )


def _preload_stations():
    """Instead of asking Postgres for each station, preload the geometries."""
    stations = []
    for station, insee in db.session.query(
        Station, Town.insee
    ).join(Town):
        stations.append({
            'object': station,
            'geometry': to_shape(station.location),
            'insee': insee,  # so we can quickly ignore stations out of the taxi's zone
        })
    return stations


def _preload_allowed_insee():
    """A taxi from a given town is allowed in other towns of the same ZUPC."""
    allowed_insee = collections.defaultdict(list)
    # too bad we're loading the full objects for a single field
    for zupc in ZUPC.query.options(joinedload(Town, ZUPC.allowed)):
        zupc_allowed = [town.insee for town in zupc.allowed]
        for town in zupc.allowed:
            allowed_insee[town.insee].extend(zupc_allowed)

    return allowed_insee


def _fetch_telemetries(last_run, now):
    """Fetch details for taxis reporting a position between the last run and now."""
    taxi_ids = []
    pipeline = current_app.redis.pipeline()
    for taxi_operator in current_app.redis.zrangebyscore('timestamps', last_run, now):
        taxi_id, operator = taxi_operator.decode('utf8').split(':')
        pipeline.hget(f'taxi:{taxi_id}', operator)
        taxi_ids.append(taxi_id)

    # Fetch their latest position from geotaxi
    telemetries = {}
    for taxi_id, telemetry in zip(taxi_ids, pipeline.execute()):
        telemetries[taxi_id] = redis_backend._Taxi.from_redis(telemetry)

    return telemetries


def _fetch_availability():
    not_available = set()
    for taxi_operator in current_app.redis.zrange('not_available', 0, -1):
        taxi_id, _operator = taxi_operator.decode('utf-8').split(':')
        not_available.add(taxi_id)
    return not_available


def _fetch_taxi_insee(taxi_ids):
    taxi_insee = {
        taxi_id: insee for taxi_id, insee in db.session.query(
            Taxi.id, ADS.insee
        ).filter(
            Taxi.id.in_(taxi_ids)
        ).join(Taxi.ads)
    }
    return taxi_insee


def _fetch_station_data(telemetries):
    """Fetch previous station data from this subset of free taxis"""
    pipeline = current_app.redis.pipeline()

    pipeline = current_app.redis.pipeline()
    for taxi_id in telemetries:  # Only the free taxis this time
        pipeline.hgetall(f'station:{taxi_id}')

    station_data = {}
    for taxi_id, res in zip(telemetries, pipeline.execute()):
        station_data[taxi_id] = StationData.from_redis(res)

    return station_data


def _find_station(stations, point, allowed_insee):
    """Find the station the given point is located at.

    A point is considered at a station 50 meters around (French regulation).

    (Side note: Paris Taxis was using 25 meters.)
    """
    valid_stations = []
    for station in stations:
        # Quickly ignore stations not allowed for this taxi
        if station['insee'] not in allowed_insee:
            continue
        distance = station['geometry'].distance(point)
        if distance > 50:  # 50 meters
            continue
        valid_stations.append({
            'object': station['object'],
            'distance': distance,
        })

    if not valid_stations:
        return None

    # When in doubt with several stations matching, pick the closest one
    station = min(valid_stations, key=operator.itemgetter('distance'))
    return station['object']


@celery.task(name='compute_waiting_taxis_stations')
def compute_waiting_taxis_stations():
    """If a taxi hasn't moved much since the last run, check if their position is in the range of a station.
    """
    now = int(time.time())
    # Limit to new telemetries since this task was last run
    last_run = current_app.redis.get('compute_waiting_taxis_stations')
    if last_run:
        last_run = int(last_run)
    else:
        last_run = now - STATION_DATA_TIMEOUT
    current_app.logger.info('Run task compute_waiting_taxis_stations for telemetries received after %s', last_run)

    # Preload stations with their geometry, faster than asking Postgres each time
    stations = _preload_stations()
    # We need the list of allowed towns for a given taxi (we can probably cache it for long periods)
    allowed_insee = _preload_allowed_insee()

    step1 = time.time()
    current_app.logger.debug(' - Step 1: static data preloaded in %f', (step1 - now))

    # Quickly select the taxis with fresh telemetry data
    telemetries = _fetch_telemetries(last_run, now)
    not_available = _fetch_availability()
    taxi_insee = _fetch_taxi_insee(telemetries)

    step2 = time.time()
    current_app.logger.debug(' - Step 2: taxi data fetch in %f', (step2 - step1))
    current_app.logger.info('    - Found %d taxis to check', len(telemetries))

    pipeline = current_app.redis.pipeline()
    stats = collections.Counter()

    # Process to compare the current position with the last one recorded
    for taxi_id, previous_station_data in _fetch_station_data(telemetries).items():
        # If we receive a taxi ID in Redis but not in Postgres, ignore it
        if taxi_id not in taxi_insee:
            stats['invalid'] += 1
            continue
        if taxi_id in not_available:
            stats['not_available'] += 1
            continue
        telemetry = telemetries[taxi_id]
        station_id = ''  # Reset by default
        if previous_station_data:
            # Is previous data still valid
            if now - previous_station_data.timestamp <= STATION_DATA_TIMEOUT:
                # Fast path if the position hasn't changed (should it happen in real life)
                if (previous_station_data.station_id
                        and telemetry.lat == previous_station_data.lat
                        and telemetry.lon == previous_station_data.lon):
                    station_id = previous_station_data.station_id
                    stats['static'] += 1
                else:
                    if USE_GEODESIC:
                        distance = geodesic(  # Slower but more precise
                            (telemetry.lat, telemetry.lon),
                            (previous_station_data.lat, previous_station_data.lon),
                        )
                    else:
                        distance = great_circle(  # Faster but less precise
                            (telemetry.lat, telemetry.lon),
                            (previous_station_data.lat, previous_station_data.lon),
                        )
                    # If the taxi hasn't "moved" from last run, spend time to find its station
                    # The taxi could be parked but still move one place because the one ahead just left with
                    # a client aboard, and GPS values jitter naturally.
                    if distance.meters <= TAXI_DISTANCE_JITTER:
                        point = Point(telemetry.lon, telemetry.lat)
                        station = _find_station(stations, point, allowed_insee[taxi_insee[taxi_id]])
                        if station:
                            station_id = station.id
                            stats['parked_in_station'] += 1
                        else:
                            stats['parked_outside_station'] += 1
                    else:
                        stats['moving'] += 1
            else:
                stats['old'] += 1
        else:
            # The first time, just store a new taxi
            stats['new'] += 1
        # Insert or update taxi data for the next time the task runs
        pipeline.hset(f'station:{taxi_id}', mapping={
            'timestamp': now,
            'lat': telemetry.lat,
            'lon': telemetry.lon,
            'station_id': station_id,
        })
        # Insert data specifically for the "live stations" endpoint
        if station_id:
            pipeline.zadd('stations_live', {f'{station_id}:{taxi_id}': now})

    step3 = time.time()
    current_app.logger.debug(' - Step 3: stations computed in %f', (step3 - step2))
    current_app.logger.debug('   - stats: %s', stats)

    pipeline.set('compute_waiting_taxis_stations', str(now))
    pipeline.execute()

    end = time.time()
    current_app.logger.debug(' - Step 4: redis updated in %f', (end - step3))

    current_app.logger.info('Done computing taxis waiting in stations in %f', end - now)
