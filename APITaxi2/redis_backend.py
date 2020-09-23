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
    status: str
    device: str
    version: int


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
    returns all updates between two times.

    The asynchronous task clean_geotaxi_timestamps removes taxis with a
    location older than 2 minutes. If the task runs correctly, no results older
    than 2 minutes will be returned."""
    ret = []
    rows = current_app.redis.zrangebyscore('timestamps', start_timestamp, end_timestamp, withscores=True)
    for row in rows:
        taxi_operator, timestamp = row
        taxi_id, operator = taxi_operator.decode('utf8').split(':')
        ret.append(_TaxiLocationUpdate(taxi_id=taxi_id, operator=operator, timestamp=int(timestamp)))
    return ret


def list_taxis(start_timestamp, end_timestamp):
    """When a location is received by geotaxi, the hash key "taxi:<taxi_id>" is
    created.

    This function:

    - calls KEYS taxi:* to list all taxis
    - for each entry, calls HGETALL taxi:*
    - if the update date is between start_timestamp and end_timestamp, return the result.

    This is to keep backward compatibility, but statistics need to be
    reworked completely. There are several problems here:

    - executing KEYS taxi:* then HGETALL on each entry takes too much time, and
      will not scale.
    - if we receive a location update for a non-existing taxi, geotaxi creates
      an entry in redis.
    - in the case a taxi is connected with several applications, we return
      several entries for this taxi
    """
    pipeline = current_app.redis.pipeline()
    rows = current_app.redis.keys('taxi:*')
    taxi_ids = []

    # Call KEYS taxi:*. For each entry, call HGETALL taxi:<id> from the pipeline.
    # We use a pipeline to improve speed because listing all taxis may return many results.
    for row in current_app.redis.keys('taxi:*'):
        taxi_id = row.decode('utf8')[len('taxi:'):]
        pipeline.hgetall('taxi:%s' % taxi_id)
        taxi_ids.append(taxi_id)

    ret = []

    # updates is a dict, where keys are operators names and values a string
    # containing the timestamp, lat, lon, status, device and version.
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
    key = '%s:%s' % (taxi_id, taxi_operator.email)
    if available:
        current_app.redis.zrem(redis_key, key)
    else:
        current_app.redis.zadd('not_available', {key: 0})


def log_taxi_status(taxi_id, status):
    """Log `status` into the ZSET "taxi_status:<taxi_id>".

    XXX: this is probably useless. We keep this logging feature for
    compatibility purpose with APITaxi v1 but logs are not easy to process
    as-is, and I am not sure we need or even use these logs anyway."""
    now = time.time()
    key = '%s_%s' % (status, now)
    value = now

    current_app.redis.zadd('taxi_status:%s' % taxi_id, {key: value})


@dataclass
class _Location:
    lon: float
    lat: float
    distance: float
    update_date: datetime


def taxis_locations_by_operator(lon, lat, distance):
    """Get the list of taxis positions from the redis geoindex "geoindex_2",
    which is populated by geotaxi.
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

        locations[taxi_id][operator] = _Location(
            lon=location[0],
            lat=location[1],
            distance=distance,
            update_date=update_date
        )
    return locations


def log_hail(hail_id, http_method, request_payload, hail_initial_status,
             request_user, response_payload, response_status_code):
    """When a request creates or changes a hail, we log it into redis. This is
    for backward compatibility purpose. It would probably be better to have a
    generic logging module and log all modifications.
    """
    key = 'hail:%s' % hail_id
    data = {
        'method': http_method,
        'payload': json.dumps(request_payload, indent=2),
        'initial_status': hail_initial_status,
        'user': request_user.email,
        'code': response_status_code,
        'return': json.dumps(response_payload, indent=2)
    }
    current_app.redis.zadd(key, {json.dumps(data): time.time()})
    current_app.redis.expire(key, timedelta(weeks=+6))
