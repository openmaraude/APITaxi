"""This module gathers functions to access data stored in redis."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import time

from flask import current_app


@dataclass
class _Taxi:
    timestamp: int
    lat: float
    lon: float
    # The following fields are deprecated
    status: str  # light status, unused
    device: str  # usually "phone" or "mobile", unused
    version: int  # should be "2", unused


def get_taxi(taxi_id, operator_name):
    """geotaxi-python receives taxi positions and store them into redis. This
    function executes the redis call `HGET taxi:user` which returns:

    >>> b'<timestamp> <lat> <lon> <taxi_status> <device name> <version>'
    """
    res = current_app.redis.hget('taxi:%s' % taxi_id, operator_name)
    if not res:
        return None

    timestamp, lat, lon, status, device, version = res.decode('utf8').split()
    return _Taxi(
        timestamp=int(timestamp),
        lat=float(lat),
        lon=float(lon),
        status=status,
        device=device,
        version=int(version)
    )


@dataclass
class _TaxiLocationUpdate:
    taxi_id: str
    operator: str
    timestamp: int


def get_timestamps_entries_between(start_timestamp, end_timestamp):
    """Geotaxi stores taxis updates in the zset "timestamps". This function
    returns all updates between two timestamps.

    The asynchronous task clean_geoindex_timestamps removes taxis with a
    location older than 2 minutes, so any older entry is not guaranteed to be
    returned."""
    ret = []
    rows = current_app.redis.zrangebyscore('timestamps', start_timestamp, end_timestamp, withscores=True)
    for row in rows:
        taxi_operator, timestamp = row
        taxi_id, operator = taxi_operator.decode('utf8').split(':')
        ret.append(_TaxiLocationUpdate(taxi_id=taxi_id, operator=operator, timestamp=int(timestamp)))
    return ret


def list_taxi_ids():
    """Simply list all the taxi IDs known to Redis."""
    PREFIX = len(b'taxi:')

    for index in current_app.redis.scan_iter('taxi:*'):
        yield index[PREFIX:].decode('utf8')


def list_taxis(start_timestamp, end_timestamp):
    """Geotaxi creates the hash key "taxi:<taxi_id>" when it receives a
    location.

    This function:

    - SCAN taxi:* to list all taxis
    - for each entry, calls HGETALL taxi:*
    - if the update date is between start_timestamp and end_timestamp, return
      the result.

    This is to keep backward compatibility, but statistics need to be
    reworked completely. There are several problems here:

    - executing SCAN taxi:* then HGETALL on each entry takes a lot of time, and
      will not scale with thousands of entries.
    - if we receive a location update for a non-existing taxi, geotaxi creates
      an entry in redis.
    - in the case a taxi is connected with several applications, we return
      several entries for this taxi
    """
    pipeline = current_app.redis.pipeline()
    taxi_ids = []
    PREFIX = len(b'taxi:')

    # Iterate on keys taxi:*. For each entry, call HGETALL taxi:<id> in the pipeline.
    # We use a pipeline to improve speed because listing all taxis may return many results.
    for index in current_app.redis.scan_iter('taxi:*'):
        taxi_id = index[PREFIX:].decode('utf8')
        pipeline.hgetall(index)
        taxi_ids.append(taxi_id)

    ret = []

    # `updates` is a dict where the key is the operator name, and value a
    # string containing the timestamp, lat, lon, status, device and version.
    for taxi_id, updates in zip(taxi_ids, pipeline.execute()):
        for operator, update in updates.items():
            operator = operator.decode('utf8')
            timestamp, lat, lon, status, device, version = update.decode('utf8').split()
            timestamp = int(float(timestamp))

            if timestamp >= start_timestamp and timestamp <= end_timestamp:
                ret.append(_TaxiLocationUpdate(taxi_id=taxi_id, operator=operator, timestamp=timestamp))
    return ret


def set_taxi_availability(taxi_id, taxi_operator, available):
    """Add or remove the entry "<taxi_id>:<operator>" from the ZSET
    "not_available"."""
    redis_key = 'not_available'
    key = '%s:%s' % (taxi_id, taxi_operator)
    if available:
        current_app.redis.zrem(redis_key, key)
    else:
        current_app.redis.zadd(redis_key, {key: 0})


def list_taxi_positions(taxi_ids):
    # We don't try to map a taxi to its position, just a cloud of points
    return current_app.redis.geopos('geoindex', *taxi_ids)


@dataclass
class Location:
    lon: float
    lat: float
    distance: float
    update_date: datetime


def taxis_locations_by_operator(lon, lat, distance):
    """Get the list of taxis positions from the redis geoindex "geoindex_2",
    which is populated by geotaxi.

    Returns a dictionary such as:

    >>> {
    ...    <taxi_id>: {
    ...       <operator_email>: Location object,
    ...       <operator_email>: Location object,
    ...       ...
    ...    }
    ... }
    """
    locations = {}
    data = current_app.redis.georadius(
        'geoindex_2',
        lon,
        lat,
        distance,
        unit='m',
        withdist=True,
        withcoord=True,
        sort='ASC'
    )
    for row in data:
        taxi_operator, distance, location = row
        taxi_id, operator = taxi_operator.decode('utf8').split(':')

        if taxi_id not in locations:
            locations[taxi_id] = {}

        update_date = current_app.redis.zscore('timestamps', '%s:%s' % (taxi_id, operator))
        if update_date:
            update_date = datetime.fromtimestamp(update_date)

        locations[taxi_id][operator] = Location(
            lon=location[0],
            lat=location[1],
            distance=distance,
            update_date=update_date
        )
    return locations


def log_hail(hail_id, http_method, request_payload, hail_initial_status,
             request_user=None, response_payload=None,
             response_status_code=None, hail_final_status=None):
    """When a request creates or changes a hail, we log it into redis. This is
    for backward compatibility purpose. It would probably be better to have a
    generic logging module and log all modifications."""
    key = 'hail:%s' % hail_id
    data = {
        'method': http_method,
        'payload': request_payload,
        'initial_status': hail_initial_status
    }

    if request_user:
        data['user'] = request_user.email
    if response_status_code:
        data['code'] = response_status_code
    if response_payload:
        data['return'] = response_payload
    if hail_final_status:
        data['final_status'] = hail_final_status

    current_app.redis.zadd(key, {json.dumps(data): time.time()})
    current_app.redis.expire(key, timedelta(weeks=+6))


def set_fake_taxi_ids(current_user, fake_taxi_ids):
    current_app.redis.hset(f'fake_taxi_id:{current_user.email}', mapping=fake_taxi_ids)
    current_app.redis.expire(f'fake_taxi_id:{current_user.email}', timedelta(hours=1))


def get_real_taxi_id(current_user, fake_taxi_id):
    # Redis-py returns bytes, which is impractical
    real_taxi_id = current_app.redis.hget(f'fake_taxi_id:{current_user.email}', fake_taxi_id)
    if real_taxi_id:
        return real_taxi_id.decode()
    # Assume already real taxi ID (e.g. simulator)
    return fake_taxi_id
