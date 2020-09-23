"""This module gathers functions to access data stored in influxdb."""

import datetime

from flask import current_app


def get_nb_active_taxis(insee_code):
    """Returns the number of active taxis stored by the celery cron
    `store_active_taxis`."""
    query = '''
        SELECT "value"
        FROM "nb_taxis_every_1"
        WHERE "zupc" = '%s'
        AND "operator" = ''
        AND time > NOW() - 1m FILL(null) LIMIT 1;
    ''' % insee_code
    try:
        resp = current_app.influx.query(query)
    except Exception as exc:
        current_app.logger.warning('Unable to query influxdb: %s', exc)
        return None

    points = list(resp.get_points())
    # InfluxDB is available, but there is no active taxi reported.
    if not points:
        return 0

    ret = points[0].get('value')
    return ret


def log_value(measurement, tags, value=1):
    try:
        current_app.influx.write_points([{
            'measurement': measurement,
            'tags': tags,
            'time': datetime.datetime.utcnow().strftime('%Y%m%dT%H:%M:%SZ'),
            'fields': {
                'value': value
            }
        }])
        return True
    except Exception as exc:
        current_app.logger.warning('Unable to query influxdb: %s', exc)
        return False
