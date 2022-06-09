"""This module gathers functions to access data stored in time series tables."""

import datetime

from flask import current_app

from APITaxi_models2 import db
from APITaxi_models2.stats import *


def get_stats_model(measurement, insee, zupc, operator):
    model_name = ['stats']
    every = {
        1: 'minute',
        60: 'hour',
        1440: 'day',
        10080: 'week',
    }[measurement]
    model_name.append(every)
    if operator:
        model_name.append('operator')
    if insee:
        model_name.append('insee')
    elif zupc:
        model_name.append('zupc')
    model_name = '_'.join(model_name)
    return globals()[model_name]


def get_nb_active_taxis(insee_code=None, zupc_id=None, operator=None):
    """Returns the number of active taxis stored by the celery cron
    `store_active_taxis`."""
    model = get_stats_model(1, insee_code, zupc_id, operator)
    query = db.session.query(model.value).filter(
        model.time > datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
    )
    if insee_code:
        query = query.filter(model.insee == insee_code)
    if zupc_id:
        query = query.filter(model.zupc == zupc_id)
    if operator:
        query = query.filter(model.operator == operator)
    resp = query.limit(1).scalar()

    # No active taxi reported.
    if not resp:
        return 0

    return resp


def log_value(measurement, value=1, insee=None, zupc=None, operator=None):
    model = get_stats_model(measurement, insee, zupc, operator)
    instance = model(
        time=datetime.datetime.utcnow(),
        value=value,
    )
    if insee:
        instance.insee = insee
    if zupc:
        instance.zupc = zupc
    if operator:
        instance.operator = operator
    with db.session.begin_nested() as nested:
        try:
            db.session.add(instance)
            db.session.flush()
            return True
        except Exception as exc:
            nested.rollback()
            current_app.logger.warning('Unable to query stats: %s', exc)
            return False
    # The caller must commit() in the end!
