"""This module gathers functions to access data stored in influxdb."""

from flask import current_app
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError


def _get_client():
    """Build InfluxDBClient with parameters from configuration."""
    sentinel = object()
    params = {}
    for arg in (
        'host', 'port',
        'username', 'password',
        'ssl', 'verify_ssl',
        'timeout',
        'use_udp', 'udp_port',
        'database'

    ):
        value = current_app.config.get('INFLUXDB_%s' % arg.upper(), sentinel)
        if value is sentinel:
            continue
        params[arg] = value

    return InfluxDBClient(**params)


def get_nb_active_taxis(insee_code):
    """Number of active taxis are stored by a celery cron. This function
    returns the number of taxis stored. If influxdb is unavailable, None is
    returned."""
    client = _get_client()
    query = '''
        SELECT "value"
        FROM "nb_taxis_every_1"
        WHERE "zupc" = '%s'
        AND "operator" = ''
        AND time > NOW() - 1m FILL(null) LIMIT 1;
    ''' % insee_code
    try:
        resp = client.query(query)
    except Exception as exc:
        current_app.logger.warning('Unable to query influxdb: %s', exc)
        return None

    points = list(resp.get_points())
    # InfluxDB is available, but there is no active taxi reported.
    if not points:
        return 0

    ret = points[0].get('value')
    return ret
