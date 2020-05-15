"""This module gathers functions to access data stored in redis."""

from dataclasses import dataclass

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
