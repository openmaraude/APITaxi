"""This module gathers functions to access data stored in influxdb."""

from flask import current_app
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError


def _get_client():
    """Build InfluxDBClient with parameters from configuration.
    """
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


def get_active_taxis(insee_code):
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
        current_app.logger.error('Unable to query influxdb: %s', exc)
        return None

    points = list(resp.get_points())
    if not points:
        return None

    ret = points[0].get('value')
    return ret
