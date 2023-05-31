"""Store statistics into time series tables."""

import collections
from datetime import datetime
import time

from celery import shared_task
from flask import current_app
from sqlalchemy.orm import joinedload

from APITaxi_models2 import db, Taxi, Town, User, VehicleDescription, ZUPC

from .. import stats_backend
from .. import redis_backend


def _log_active_taxis(last_update, data):
    """Given a dictionary where keys are Taxi objects, and values list of
    VehicleDescription, log data in postgres.

    The following entries are written into the stats_xxx tables:

    - value total
    - value grouped by insee
    - value grouped by zupc
    - value grouped by operator
    - value grouped by insee and operator
    - value grouped by zupc and operator
    """
    stats_backend.log_value(
        last_update,
        value=len(data)
    )

    # Count data by insee code
    taxis_by_insee = collections.Counter(taxi.ads.insee for taxi in data)

    # Group data by insee code
    for insee in sorted(taxis_by_insee):
        stats_backend.log_value(
            last_update,
            **{
                'insee': insee  # Insee code used as the key
            },
            value=taxis_by_insee[insee]
        )

    # Group by ZUPC
    covered_zupc = db.session.query(ZUPC).options(
        joinedload(ZUPC.allowed)
    ).filter(
        ZUPC.allowed.any(Town.insee.in_(taxis_by_insee))
    ).all()
    for zupc in covered_zupc:
        nb_taxis = sum(taxis_by_insee[town.insee] for town in zupc.allowed)
        stats_backend.log_value(
            last_update,
            **{
                'zupc': zupc.zupc_id
            },
            value=nb_taxis
        )

    # Group by operator
    operators = collections.Counter(
        desc.added_by.email for descriptions in data.values() for desc in descriptions
    )

    for operator, num_active in operators.items():
        stats_backend.log_value(
            last_update,
            **{
                'operator': operator
            },
            value=num_active
        )

    # Group by town and operator
    town_operators = collections.Counter()
    for taxi, descriptions in data.items():
        for description in descriptions:
            if description.status == 'free':
                town_operators[(taxi.ads.insee, description.added_by.email)] += 1

    for (insee, operator), num_active in town_operators.items():
        stats_backend.log_value(
            last_update,
            **{
                'operator': operator,
                'insee': insee
            },
            value=num_active
        )

    # Group by ZUPC and operator
    zupc_operators = collections.Counter()
    for zupc in covered_zupc:
        for taxi, descriptions in data.items():
            if taxi.ads.insee not in [town.insee for town in zupc.allowed]:
                continue
            for description in descriptions:
                if description.status == 'free':
                    zupc_operators[(zupc.zupc_id, description.added_by.email)] += 1

    for (zupc_id, operator), num_active in zupc_operators.items():
        stats_backend.log_value(
            last_update,
            **{
                'operator': operator,
                'zupc': zupc_id
            },
            value=num_active
        )


@shared_task(name='store_active_taxis')
def store_active_taxis(last_update):
    """Store statistics into time series tables of taxis with a location update
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
    taxi_ids = {update.taxi_id: update.operator for update in updates}

    to_log = collections.defaultdict(list)
    for taxi, vehicle_description in db.session.query(Taxi, VehicleDescription).join(
        User,
        VehicleDescription.added_by_id == User.id
    ).options(
        joinedload(Taxi.ads),
        joinedload(VehicleDescription.added_by)
    ).filter(
        Taxi.vehicle_id == VehicleDescription.vehicle_id
    ).filter(
        Taxi.id.in_(taxi_ids.keys()),
        User.email.in_(taxi_ids.values()),
    ):
        # As we ask a broader combination of taxis and their operators, filter out now
        operator = taxi_ids[taxi.id]
        if vehicle_description.added_by.email != operator:
            continue
        to_log[taxi].append(vehicle_description)

    _log_active_taxis(last_update, to_log)
    db.session.commit()
