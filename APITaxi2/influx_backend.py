"""This module gathers functions to access data stored in influxdb."""

import datetime

from flask import current_app

from APITaxi_models2 import db, nb_taxis_every


def get_nb_active_taxis(insee_code=None, zupc_id=None, operator=None):
    """Returns the number of active taxis stored by the celery cron
    `store_active_taxis`."""
    query = db.session.query(nb_taxis_every.value).filter(
        nb_taxis_every.measurement == 1,
        nb_taxis_every.time > datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
    )
    if insee_code:
        query = query.filter(nb_taxis_every.insee == insee_code)
    if zupc_id:
        query = query.filter(nb_taxis_every.zupc == zupc_id)
    if operator:
        query = query.filter(nb_taxis_every.operator == operator)
    resp = query.limit(1).scalar()

    # No active taxi reported.
    if not resp:
        return 0

    return resp


def log_value(measurement, tags, value=1):
    with db.session.begin_nested() as nested:
        try:
            db.session.add(nb_taxis_every(
                measurement=measurement,
                time=datetime.datetime.utcnow(),
                value=value,
                insee=tags.get('insee'),
                zupc=tags.get('zupc'),
                operator=tags.get('operator'),
            ))
            db.session.flush()
            return True
        except Exception as exc:
            nested.rollback()
            current_app.logger.warning('Unable to query influxdb: %s', exc)
            return False
    # The caller must commit() in the end!
