"""This module gathers functions to access data stored in redis."""

from dataclasses import dataclass
import time

from flask import current_app


@dataclass
class _Taxi:
    timestamp : int
    lat : float
    lon : float
    status : str
    device : str
    version : int


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
