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
