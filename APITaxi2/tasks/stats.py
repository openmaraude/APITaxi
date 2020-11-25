"""Store statistics into influxdb."""

import collections
from datetime import datetime
import itertools
import time

from flask import current_app
from sqlalchemy.orm import joinedload

from APITaxi_models2 import ADS, db, Taxi, User, VehicleDescription, ZUPC

from . import celery
from .. import influx_backend
from .. import redis_backend


def _log_active_taxis(last_update, data):
    """Given a dictionary where keys are Taxi objects, and values list of
    VehicleDescription, log data in influx.

    The following entries are written into influx:

    - measurement=nb_taxis_every_<last_update>
    - measurement=nb_taxis_every_<last_update> grouped by zupc
    - measurement=nb_taxis_every_<last_update> grouped by operator
    - measurement=nb_taxis_every_<last_update> grouped by zupc and operator
    """
    influx_backend.log_value(
        'nb_taxis_every_%s' % last_update,
        {},
        value=len(data)
    )

    # Sort then group data by insee code
    for insee, group in itertools.groupby(
        sorted(data, key=lambda taxi: taxi.ads.zupc.parent.insee),
        key=lambda taxi: taxi.ads.zupc.parent.insee
    ):
        influx_backend.log_value(
            'nb_taxis_every_%s' % last_update,
            {
                'zupc': insee
            },
            value=len(list(group))
        )

    # Group by operator
    operators = collections.defaultdict(int)
    for taxi, descriptions in data.items():
        for description in descriptions:
            operators[description.added_by.email] += 1

    for operator, num_active in operators.items():
        influx_backend.log_value(
            'nb_taxis_every_%s' % last_update,
            {
                'operator': operator
            },
            value=num_active
        )

    # Group by ZUPC and operator
    zupc_operators = collections.defaultdict(lambda: collections.defaultdict(int))
    for taxi, descriptions in data.items():
        for description in descriptions:
            if description.status == 'free':
                zupc_operators[taxi.ads.zupc.parent.insee][description.added_by.email] += 1

    for insee, values in zupc_operators.items():
        for opeartor, num_active in values.items():
            influx_backend.log_value(
                'nb_taxis_every_%s' % last_update,
                {
                    'operator': operator,
                    'zupc': insee
                },
                value=num_active
            )


@celery.task(name='store_active_taxis')
def store_active_taxis(last_update):
    """Store statistics into influxdb of taxis with a location update
    made since `last_update` minutes ago.

    This function is a readable rewrite from the old API, but it generates a
    lot of SQL queries and still needs to be refactored.
    """
    end_time = int(time.time())
    start_time = end_time - (last_update * 60)

    current_app.logger.info(
        'Store active taxis (%s) between %s (%s) and %s (%s)',
        last_update,
        start_time, datetime.fromtimestamp(start_time),
        end_time, datetime.fromtimestamp(end_time)
    )

    # The asynchronous task clean_geoindex_timestamps removes entries from the
    # ZSET "timestamps" that are older than 2 minutes.
    # To generate the statistics for data older than 2 minutes, use the slow
    # path with list_taxis().
    if last_update <= 2:
        updates = redis_backend.get_timestamps_entries_between(start_time, end_time)
    else:
        updates = redis_backend.list_taxis(start_time, end_time)

    to_log = collections.defaultdict(list)
    for update in updates:
        query = db.session.query(Taxi, VehicleDescription).join(
            User,
            VehicleDescription.added_by_id == User.id
        ).options(
            joinedload(Taxi.ads)
            .joinedload(ADS.zupc)
            .joinedload(ZUPC.parent)
        ).options(
            joinedload(VehicleDescription.added_by)
        ).filter(
            Taxi.vehicle_id == VehicleDescription.vehicle_id
        ).filter(
            User.email == update.operator,
            Taxi.id == update.taxi_id
        )

        res = query.one_or_none()
        if not res:
            current_app.logger.warning(
                'Taxi %s with operator %s exists in redis but not in postgresql. Skip it.',
                update.taxi_id, update.operator
            )
            continue

        taxi, vehicle_description = res
        to_log[taxi].append(vehicle_description)

    _log_active_taxis(last_update, to_log)
