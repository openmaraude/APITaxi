import datetime
import json

from flask import Blueprint, request
from flask_security import current_user, login_required, roles_accepted
from sqlalchemy import func, Text, DateTime, Numeric
from sqlalchemy.dialects.postgresql import JSONB

from APITaxi_models2 import db, ArchivedHail, Hail, Role, Taxi, User, VehicleDescription
from APITaxi_models2.stats import stats_hour

from .. import schemas


blueprint = Blueprint('stats', __name__)
threshold = datetime.datetime(2022, 1, 1)


"""
Nombre de courses distribuées par mois sur deux ans
Moyenne de courses 2021 + 2022 + 3 derniers mois

Nombre de courses sur les trois derniers mois (+ que Lyon)
"""

def get_intervals():
    now = datetime.datetime.now()
    return [
        now - datetime.timedelta(4 * 3),  # 3 months ago
        now - datetime.timedelta(4 * 6),  # 6 months ago
        now - datetime.timedelta(days=365)  # 12 months ago
    ]


def get_last_three_months_interval():
    today = datetime.date.today()
    return [today - datetime.timedelta(weeks=4 * 3), today]  # ongoing day excluded


def get_current_year_interval():
    current_year = datetime.date.today().year
    return [datetime.date(current_year, 1, 1), datetime.date(current_year + 1, 1, 1)]  # upper bound excluded


def get_last_year_interval():
    current_year = datetime.date.today().year
    last_year = current_year - 1
    return [datetime.date(last_year, 1, 1), datetime.date(current_year, 1, 1)]  # upper bound excluded


@blueprint.route('/stats/taxis', methods=['GET'])
@login_required
@roles_accepted('admin')
def stats_taxis():
    def get_registered_taxis(since=None, until=None):
        query = Taxi.query
        if since:
            query = query.filter(Taxi.added_at >= since)
        if until:
            query = query.filter(Taxi.added_at < until)
        return query.count()

    def get_connected_taxis(since=None, until=None):
        query = Taxi.query.filter(Taxi.last_update_at.isnot(None))
        if since:
            query = query.filter(Taxi.last_update_at >= since)
        if until:
            query = query.filter(Taxi.last_update_at < until)
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
        return {int(k): float(v) for k, v in query}

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
        query = db.session.query(
            func.Count(VehicleDescription.radius) * 100.0 / func.Count()
        )
        return query.scalar()

    three_months_ago, six_months_ago, twelve_months_ago = get_intervals()
    schema = schemas.DataStatsTaxisSchema()
    return schema.dump({'data': [{
        'registered_taxis': {
            'today': get_registered_taxis(),
            'three_months_ago': get_registered_taxis(until=three_months_ago),
            'six_months_ago': get_registered_taxis(until=six_months_ago),
            'twelve_months_ago': get_registered_taxis(until=twelve_months_ago),
        },
        'connected_taxis': {
            'today': get_connected_taxis(),
            'three_months_ago': get_connected_taxis(until=three_months_ago),
            'six_months_ago': get_connected_taxis(until=six_months_ago),
            'twelve_months_ago': get_connected_taxis(until=twelve_months_ago),
        },
        'registered_taxis_since_threshold': {
            'today': get_registered_taxis(since=threshold),
            'three_months_ago': get_registered_taxis(since=threshold, until=three_months_ago),
            'six_months_ago': get_registered_taxis(since=threshold, until=six_months_ago),
            'twelve_months_ago': get_registered_taxis(since=threshold, until=twelve_months_ago),
        },
        'connected_taxis_since_threshold': {
            'today': get_connected_taxis(since=threshold),
            'three_months_ago': get_connected_taxis(since=threshold, until=three_months_ago),
            'six_months_ago': get_connected_taxis(since=threshold, until=six_months_ago),
            'twelve_months_ago': get_connected_taxis(since=threshold, until=twelve_months_ago),
        },
        'connected_taxis_per_hour': get_connected_taxis_per_hour(threshold),
        'monthly_hails_per_taxi': get_monthly_hails_per_taxi(),
        'average_radius': get_average_radius(),
        'average_radius_change': get_average_radius_change(),
    }]})


@blueprint.route('/stats/hails', methods=['GET'])
@login_required
@roles_accepted('admin')
def stats_hails():
    def get_hails_received(since=None, until=None):
        active = Hail.query
        if since:
            active = active.filter(Hail.added_at >= since)
        if until:
            active = active.filter(Hail.added_at < until)
        archived = ArchivedHail.query
        if since:
            archived = archived.filter(ArchivedHail.added_at >= since)
        if until:
            archived = archived.filter(ArchivedHail.added_at < until)
        return active.count() + archived.count()

    def get_hail_average(interval, since=None, until=None, status=None):
        def _get_hail_average(model):
            counts = db.session.query(func.Count()).select_from(model)
            if since:
                counts = counts.filter(model.added_at >= since)
            if until:
                counts = counts.filter(model.added_at < until)
            if status:
                counts = counts.filter(model.status == status)
            counts = counts.group_by(func.date_trunc(interval, model.added_at))
            counts = counts.subquery()
            query = db.session.query(func.Avg(counts.c.count))
            return query.scalar() or 0
        return _get_hail_average(Hail) + _get_hail_average(ArchivedHail)

    def get_average_transition_time(from_status, to_status):
        from_status = json.dumps({"status": from_status})
        to_status = json.dumps({"status": to_status})
        transition_log = db.session.query(
            # Having to cast transition_log to JSBON, json_path_query doesn't exist (should we convert transition_log to begin with?)
            # then having to cast to Text because Postgres can't cast from JSONB to TIMESTAMP
            # There is a datetime() function for path queries, but it doesn't recognize our ISO format, where the regular timestamp does
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

    def _get_hails_average(since, until):
        return {
            'daily': {
                'total': get_hail_average('day', since, until),
                'timeout_customer': get_hail_average('day', since, until, status='timeout_customer'),
                'declined_by_customer': get_hail_average('day', since, until, status='declined_by_customer'),
                'incident_taxi': get_hail_average('day', since, until, status='incident_taxi'),
                'declined_by_taxi': get_hail_average('day', since, until, status='declined_by_taxi'),
            },
            'weekly': {
                'total': get_hail_average('week', since, until),
                'timeout_customer': get_hail_average('week', since, until, status='timeout_customer'),
                'declined_by_customer': get_hail_average('week', since, until, status='declined_by_customer'),
                'incident_taxi': get_hail_average('week', since, until, status='incident_taxi'),
                'declined_by_taxi': get_hail_average('week', since, until, status='declined_by_taxi'),
            },
            'monthly': {
                'total': get_hail_average('month', since, until),
                'timeout_customer': get_hail_average('month', since, until, status='timeout_customer'),
                'declined_by_customer': get_hail_average('month', since, until, status='declined_by_customer'),
                'incident_taxi': get_hail_average('month', since, until, status='incident_taxi'),
                'declined_by_taxi': get_hail_average('month', since, until, status='declined_by_taxi'),
            },
        }

    three_months_ago, six_months_ago, twelve_months_ago = get_intervals()
    last_three_months = get_last_three_months_interval()
    current_year = get_current_year_interval()
    last_year = get_last_year_interval()
    schema = schemas.DataStatsHailsSchema()

    return schema.dump({'data': [{
        'hails_received': {
            'today': get_hails_received(since=threshold),
            'three_months_ago': get_hails_received(since=threshold, until=three_months_ago),
            'six_months_ago': get_hails_received(since=threshold, until=six_months_ago),
            'twelve_months_ago': get_hails_received(since=threshold, until=twelve_months_ago),
        },
        'hails_total': {
            'current_year': {},
            'last_year': {},
        },
        'hails_average': {
            'last_three_months': _get_hails_average(*last_three_months),
            'current_year': _get_hails_average(*current_year),
            'last_year': _get_hails_average(*last_year),
        },
        'average_times': {
            'accepted_by_taxi': get_average_transition_time('received_by_taxi', 'accepted_by_taxi'),
            'accepted_by_customer': get_average_transition_time('accepted_by_taxi', 'accepted_by_customer'),
            'timeout_customer': get_average_transition_time('accepted_by_taxi', 'timeout_customer'),
            'declined_by_customer': get_average_transition_time('accepted_by_taxi', 'declined_by_customer'),
            'timeout_taxi': get_average_transition_time('received_by_taxi', 'timeout_taxi'),
            'incident_taxi': get_average_transition_time('accepted_by_taxi', 'incident_taxi'),
            'customer_on_board_incident_taxi': get_average_transition_time('customer_on_board', 'incident_taxi'),
            'customer_on_board': get_average_transition_time('accepted_by_taxi', 'customer_on_board'),
        }
    }]})


@blueprint.route('/stats/groupements', methods=['GET'])
@login_required
@roles_accepted('admin')
def stats_groupements():
    def get_registered_groupements():
        query = User.query.join(User.roles).filter(Role.name == 'groupement')
        return query.count()

    def get_fleet_data():
        query = db.session.query(
            User.id,
            User.email,
            User.fleet_size,
            func.Count(Taxi.id).label('count'),
            (func.Count(Taxi.id) * 100.0 / User.fleet_size).label('ratio'),
            func.Max(Taxi.added_at).label('last_taxi')
        ).outerjoin(Taxi).join(User.roles).filter(
            Role.name == 'groupement'
        ).group_by(
            User.id,
            User.email,
            User.fleet_size,
        ).order_by(
            User.email
        )
        return query

    schema = schemas.DataStatsGroupementsSchema()
    return schema.dump({'data': [{
        'registered_groupements': get_registered_groupements(),
        'fleet_data': get_fleet_data(),
    }]})
