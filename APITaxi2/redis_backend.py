"""This module gathers functions to access data stored in redis."""

from dataclasses import dataclass

from . import redis_client


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

    >>> b'<timestamp> <lat> <lon> <taxi_status> <device name> <status> <version>'
    """
    res = redis_client.hget('taxi:%s' % taxi_id, operator_name)
    if not res:
        return None

    timestamp, lat, lon, status, device, version = res.decode('utf8').split()
    return _Taxi(
        timestamp=int(timestamp),
        lat=lat,
        lon=lon,
        status=status,
        device=device,
        version=int(version)
    )
