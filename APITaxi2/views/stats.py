import datetime
import json

from flask import Blueprint, request
from flask_security import current_user, login_required, roles_accepted
from sqlalchemy import func, Text, DateTime, Float
from sqlalchemy.dialects.postgresql import JSONB

from APITaxi_models2 import db, ArchivedHail, Hail, Role, Taxi, User, VehicleDescription
from APITaxi_models2.stats import stats_hour

from .. import schemas


blueprint = Blueprint('stats', __name__)
threshold = datetime.datetime(2022, 1, 1)


def get_connected_groupements():
    query = User.query.join(User.roles).filter(Role.name == 'groupement')
    return query.count()


def get_registered_taxis(since=None):
    query = Taxi.query
    if since:
        query = query.filter(Taxi.added_at >= since)
    return query.count()


def get_connected_taxis(since=None):
    query = Taxi.query.filter(Taxi.last_update_at.isnot(None))
    if since:
        query = query.filter(Taxi.added_at >= since)
    return query.count()


def get_connected_taxis_per_hour(since=None):
    query = db.session.query(
        func.extract('hour', stats_hour.time).label('extract'),
        func.Avg(stats_hour.value)
    ).filter(
        stats_hour.time >= threshold
    ).group_by(
        func.extract('hour', stats_hour.time),
    ).order_by('extract')
    return dict({int(k): float(v) for k, v in query})


def get_monthly_hails_per_taxi():
    counts = db.session.query(
        func.Count(Hail.id)
    ).select_from(Taxi).outerjoin(
        Hail, Hail.taxi_id == Taxi.id
    ).group_by(Taxi.id).subquery()
    query = db.session.query(
        func.Avg(counts.c.count)
    )
    return query.scalar()


def get_average_radius():
    query = db.session.query(
        func.Avg(func.coalesce(VehicleDescription.radius, 500))
    # Consider drivers not changing their radius? it doesn't change much
    # ).filter(
    #     VehicleDescription.radius.isnot(None)
    )
    return query.scalar()


def get_average_radius_change():
    total = db.session.query(
        func.Count().label('total')
    ).select_from(VehicleDescription).subquery()
    changed = db.session.query(
        func.Count().label('changed')
    ).select_from(VehicleDescription).filter(VehicleDescription.radius.isnot(None)).subquery()
    query = db.session.query(
        changed.c.changed.cast(Float()) / total.c.total
    ).select_from(total, changed)
    return query.scalar()


def get_hails_received(since=None):
    active = Hail.query
    archived = ArchivedHail.query
    if since:
        archived = archived.filter(ArchivedHail.added_at >= since)
    return active.count() + archived.count()


def get_hail_average(interval, since=None, status=None):
    counts = db.session.query(func.Count()).select_from(Hail)
    if since:
        counts = counts.filter(Hail.added_at >= since)
    if status:
        counts = counts.filter(Hail.status == status)
    counts = counts.group_by(func.date_trunc(interval, Hail.added_at))
    counts = counts.subquery()
    query = db.session.query(func.Avg(counts.c.count))
    return query.scalar()


def get_average_transition_time(from_status, to_status):
    """
    select avg(interval)
    from (
        select accepted::timestamp - received::timestamp interval
        from (
            select
                jsonb_path_query(transition_log::jsonb, '$[*] ? (@.from_status == $status).timestamp', '{"status": "accepted_by_taxi"}')::text accepted,
                jsonb_path_query(transition_log::jsonb, '$[*] ? (@.from_status == $status).timestamp', '{"status": "received"}')::text received
            from hail
        ) transition_log where accepted is not null
    ) intervals;
    """
    from_status = json.dumps({"status": from_status})
    to_status = json.dumps({"status": to_status})
    transition_log = db.session.query(
        func.jsonb_path_query(Hail.transition_log.cast(JSONB()), '$[*] ? (@.to_status == $status).timestamp', to_status).cast(Text()).label('to_status'),
        func.jsonb_path_query(Hail.transition_log.cast(JSONB()), '$[*] ? (@.to_status == $status).timestamp', from_status).cast(Text()).label('from_status'),
    ).subquery()
    intervals = db.session.query(
        (transition_log.c.to_status.cast(DateTime()) - transition_log.c.from_status.cast(DateTime())).label('interval')
    ).filter(
        transition_log.c.to_status.isnot(None)
    ).subquery()
    average = db.session.query(func.Avg(intervals.c.interval))
    return (average.scalar() or datetime.timedelta()).total_seconds()


@blueprint.route('/stats/taxis', methods=['GET'])
@login_required
@roles_accepted('admin')
def stats_taxis():
    schema = schemas.DataStatsTaxisSchema()
    return schema.dump({'data': [{
        'connected_groupements': get_connected_groupements(),
        'registered_taxis': get_registered_taxis(),
        'connected_taxis': get_connected_taxis(),
        'registered_taxis_since_threshold': get_registered_taxis(threshold),
        'connected_taxis_since_threshold': get_connected_taxis(threshold),
        'connected_taxis_per_hour': get_connected_taxis_per_hour(threshold),
        'monthly_hails_per_taxi': get_monthly_hails_per_taxi(),
        'average_radius': get_average_radius(),
        'average_radius_change': get_average_radius_change(),
    }]})

@blueprint.route('/stats/hails', methods=['GET'])
@login_required
@roles_accepted('admin')
def stats_hails():
    schema = schemas.DataStatsHailsSchema()
    return schema.dump({'data': [{
        'hails_received': get_hails_received(),
        'hails_daily': {
            'total_average': get_hail_average('day'),
            'timeout_customer_average': get_hail_average('day', status='timeout_customer'),
            'declined_by_customer_average': get_hail_average('day', status='declined_by_customer'),
            'incident_taxi_average': get_hail_average('day', status='incident_taxi'),
            'declined_by_taxi_average': get_hail_average('day', status='declined_by_taxi'),
        },
        'hails_weekly': {
            'total_average': get_hail_average('week'),
            'timeout_customer_average': get_hail_average('week', status='timeout_customer'),
            'declined_by_customer_average': get_hail_average('week', status='declined_by_customer'),
            'incident_taxi_average': get_hail_average('week', status='incident_taxi'),
            'declined_by_taxi_average': get_hail_average('week', status='declined_by_taxi'),
        },
        'hails_monthly': {
            'total_average': get_hail_average('month'),
            'timeout_customer_average': get_hail_average('month', status='timeout_customer'),
            'declined_by_customer_average': get_hail_average('month', status='declined_by_customer'),
            'incident_taxi_average': get_hail_average('month', status='incident_taxi'),
            'declined_by_taxi_average': get_hail_average('month', status='declined_by_taxi'),
        },
        'average_accepted_by_taxi_time': get_average_transition_time('received_by_taxi', 'accepted_by_taxi'),
        'average_accepted_by_customer_time': get_average_transition_time('accepted_by_taxi', 'accepted_by_customer'),
        'average_timeout_customer_time': get_average_transition_time('accepted_by_taxi', 'timeout_customer'),
        'average_declined_by_customer_time': get_average_transition_time('accepted_by_taxi', 'declined_by_customer'),
        'average_timeout_taxi_time': get_average_transition_time('received_by_taxi', 'timeout_taxi'),
        'average_incident_taxi_time': get_average_transition_time('accepted_by_taxi', 'incident_taxi'),
    }]})
