import collections
import datetime
import json

from flask import Blueprint, request, current_app
from flask_security import current_user, login_required, roles_accepted
from sqlalchemy import func, Text, DateTime, Numeric
from sqlalchemy.orm import aliased
from sqlalchemy.dialects.postgresql import JSONB, INTERVAL

from APITaxi_models2 import db, ADS, Role, Taxi, User, Vehicle, VehicleDescription
from APITaxi_models2.stats import stats_hour_insee, StatsHails

from .. import schemas


INSEE_CODES = {
    'grenoble': ('38185', '38057', '38059', '38071', '38068', '38111', '38126', '38150', '38151', '38158', '38169', '38170', '38179', '38187', '38188', '38200', '38229', '38235', '38258', '38252', '38271', '38277', '38279', '38281', '38309', '38317', '38325', '38328', '38364', '38382', '38388', '38421', '38423', '38436', '38445', '38471', '38472', '38474', '38478', '38485', '38486', '38516', '38524', '38528', '38529', '38533', '38540', '38545', '38562'),
    'lyon': ('69123', '69003', '69029', '69033', '69034', '69040', '69044', '69046', '69271', '69063', '69273', '69068', '69069', '69071', '69072', '69275', '69081', '69276', '69085', '69087', '69088', '69089', '69278', '69091', '69096', '69100', '69279', '69116', '69117', '69127', '69282', '69283', '69284', '69142', '69143', '69149', '69152', '69153', '69163', '69286', '69168', '69191', '69194', '69202', '69199', '69204', '69205', '69207', '69290', '69233', '69292', '69293', '69296', '69244', '69250', '69256', '69259', '69260', '69266'),
    'rouen': ('76540', '76005', '76020', '76039', '76056', '76069', '76088', '76095', '76108', '76103', '76116', '76131', '76157', '76165', '76178', '76212', '76216', '76222', '76231', '76237', '76273', '76475', '76282', '76313', '76319', '76322', '76350', '76354', '76366', '76367', '76377', '76378', '76391', '76402', '76410', '76429', '76436', '76451', '76448', '76457', '76464', '76474', '76484', '76486', '76497', '76498', '76513', '76514', '76536', '76550', '76558', '76560', '76561', '76575', '76591', '76599', '76614', '76617', '76631', '76634', '76636', '76640', '76608', '76681', '76682', '76705', '76709', '76717', '76750', '76753', '76759'),
}

blueprint = Blueprint('stats', __name__)
threshold = datetime.datetime(2022, 1, 1)


def get_intervals():
    return [
        func.now() - func.cast('3 months', INTERVAL()),
        func.now() - func.cast('6 months', INTERVAL()),
        func.now() - func.cast('12 months', INTERVAL()),
    ]


def get_last_three_months_interval():
    today = func.current_date()
    return [today - func.cast('3 months', INTERVAL()), today]  # ongoing day excluded


def get_current_year_interval():
    current_year = func.date_trunc('year', func.current_date())
    next_year = current_year + func.cast('1 year', INTERVAL())
    return [current_year, next_year]  # upper bound excluded


def get_last_year_interval():
    current_year = func.date_trunc('year', func.current_date())
    last_year = current_year - func.cast('1 year', INTERVAL())
    return [last_year, current_year]  # upper bound excluded


def apply_filters_to_taxis(query, area, insee):
    if area or insee:
        query = query.join(Taxi.ads)
        if area:
            insee_codes = INSEE_CODES[area]
            query = query.filter(ADS.insee.in_(insee_codes))
        if insee:
            query = query.filter(ADS.insee.like(insee + '%'))
    return query


def apply_filters_to_stats_hour(query, area, insee):
    if area:
        insee_codes = INSEE_CODES[area]
        query = query.filter(stats_hour_insee.insee.in_(insee_codes))
    if insee:
        query = query.filter(stats_hour_insee.insee.like(insee + '%'))
    return query


def apply_filters_to_hails(query, area, insee):
    if area:
        insee_codes = INSEE_CODES[area]
        query = query.filter(StatsHails.insee.in_(insee_codes))
    if insee:
        query = query.filter(StatsHails.insee.like(insee + '%'))
    return query


def apply_filters_to_users(query, area, insee):
    if area or insee:
        query = query.join(Taxi.ads)
        if area:
            insee_codes = INSEE_CODES[area]
            query = query.filter(ADS.insee.in_(insee_codes))
        if insee:
            query = query.filter(ADS.insee.like(insee + '%'))
    return query


@blueprint.route('/stats/taxis', methods=['GET'])
@login_required
@roles_accepted('admin')
def stats_taxis():
    three_months_ago, six_months_ago, twelve_months_ago = get_intervals()
    area = request.args.get('area')
    insee = request.args.get('insee')

    def get_registered_taxis(since=None, until=None):
        query = Taxi.query
        if since is not None:
            query = query.filter(Taxi.added_at >= since)
        if until is not None:
            query = query.filter(Taxi.added_at < until)
        query = apply_filters_to_taxis(query, area, insee)
        return query.count()

    def get_connected_taxis(since=None, until=None):
        query = Taxi.query.filter(Taxi.last_update_at.isnot(None))
        if since is not None:
            query = query.filter(Taxi.last_update_at >= since)
        if until is not None:
            query = query.filter(Taxi.last_update_at < until)
        query = apply_filters_to_taxis(query, area, insee)
        return query.count()

    def get_monthly_hails_per_taxi():
        counts = db.session.query(
            func.Count(StatsHails.id)
        ).select_from(Taxi).outerjoin(
            StatsHails, StatsHails.taxi_hash == func.encode(func.digest(Taxi.id, 'sha1'), 'hex')
        ).group_by(Taxi.id)
        counts = apply_filters_to_taxis(counts, area, insee)
        counts = counts.subquery()
        query = db.session.query(
            func.Avg(counts.c.count)
        )
        return query.scalar()

    def get_average_radius():
        query = db.session.query(
        # Consider drivers not changing their radius? it doesn't change much
            # func.Avg(func.coalesce(VehicleDescription.radius, 500))
        # ).filter(
        #     VehicleDescription.radius.isnot(None)
            func.Avg(VehicleDescription.radius)
        ).join(Taxi.vehicle).join(Vehicle.descriptions)
        query = apply_filters_to_taxis(query, area, insee)
        return query.scalar()

    def get_average_radius_change():
        query = db.session.query(
            func.Count(VehicleDescription.radius) * 100.0 / func.Nullif(func.Count(), 0)
        ).join(Taxi.vehicle).join(Vehicle.descriptions)
        query = apply_filters_to_taxis(query, area, insee)
        return query.scalar()

    def get_connected_taxis_per_hour(since):
        # First "rebuild" stats_hour from stats_hour_insee
        counts = db.session.query(
            func.date_trunc('hour', stats_hour_insee.time).label('trunc'),
            func.Sum(stats_hour_insee.value)
        ).group_by(
            'trunc',
        )
        if since is not None:
            counts = counts.filter(stats_hour_insee.time >= since)
        counts = apply_filters_to_stats_hour(counts, area, insee).subquery()
        # Then just keep the time
        query = db.session.query(
            func.date_part('hour', counts.c.trunc).label('part'),
            func.Avg(counts.c.sum),
        ).group_by(
            'part'
        ).order_by('part')
        return {int(k): float(v) for k, v in query}

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
        'monthly_hails_per_taxi': get_monthly_hails_per_taxi(),
        'average_radius': get_average_radius(),
        'average_radius_change': get_average_radius_change(),
        'connected_taxis_per_hour': get_connected_taxis_per_hour(threshold),
    }]})


@blueprint.route('/stats/hails', methods=['GET'])
@login_required
@roles_accepted('admin')
def stats_hails():
    three_months_ago, six_months_ago, twelve_months_ago = get_intervals()
    last_three_months = get_last_three_months_interval()
    current_year = get_current_year_interval()
    last_year = get_last_year_interval()
    area = request.args.get('area')
    insee = request.args.get('insee')

    def get_hails_received(since, until=None):
        query = StatsHails.query
        if since is not None:
            query = query.filter(StatsHails.added_at >= since)
        if until is not None:
            query = query.filter(StatsHails.added_at < until)
        query = apply_filters_to_hails(query, area, insee)
        return query.count()

    def get_hails_average_per(interval, since, until, status=None):
        counts = db.session.query(
            func.Count()
        ).filter(
            StatsHails.added_at >= since,
            StatsHails.added_at < until,
        ).group_by(
            func.date_trunc(interval, StatsHails.added_at)
        )
        if status:
            counts = counts.filter(StatsHails.status == status)
        counts = apply_filters_to_hails(counts, area, insee)
        counts = counts.subquery()
        query = db.session.query(func.Avg(counts.c.count))
        return query.scalar() or 0

    def get_average_transition_time(from_status, to_status):
        from_status = getattr(StatsHails, from_status)
        to_status = getattr(StatsHails, to_status)
        query = db.session.query(func.Avg(
            to_status - from_status
        ).filter(
            to_status.isnot(None)
        ))
        return (query.scalar() or datetime.timedelta()).total_seconds()

    def get_hails_average(since, until):
        return {
            'daily': {
                'total': get_hails_average_per('day', since, until),
                'timeout_customer': get_hails_average_per('day', since, until, status='timeout_customer'),
                'declined_by_customer': get_hails_average_per('day', since, until, status='declined_by_customer'),
                'incident_taxi': get_hails_average_per('day', since, until, status='incident_taxi'),
                'declined_by_taxi': get_hails_average_per('day', since, until, status='declined_by_taxi'),
            },
            'weekly': {
                'total': get_hails_average_per('week', since, until),
                'timeout_customer': get_hails_average_per('week', since, until, status='timeout_customer'),
                'declined_by_customer': get_hails_average_per('week', since, until, status='declined_by_customer'),
                'incident_taxi': get_hails_average_per('week', since, until, status='incident_taxi'),
                'declined_by_taxi': get_hails_average_per('week', since, until, status='declined_by_taxi'),
            },
            'monthly': {
                'total': get_hails_average_per('month', since, until),
                'timeout_customer': get_hails_average_per('month', since, until, status='timeout_customer'),
                'declined_by_customer': get_hails_average_per('month', since, until, status='declined_by_customer'),
                'incident_taxi': get_hails_average_per('month', since, until, status='incident_taxi'),
                'declined_by_taxi': get_hails_average_per('month', since, until, status='declined_by_taxi'),
            },
        }

    def get_hails_total(since, until):
        query = db.session.query(
            func.date_part('month', StatsHails.added_at).label('month'),
            func.count(),
        ).filter(
            StatsHails.added_at >= since,
            StatsHails.added_at < until
        ).group_by('month').order_by('month')
        query = apply_filters_to_hails(query, area, insee)

        return query

    schema = schemas.DataStatsHailsSchema()
    return schema.dump({'data': [{
        'hails_received': {
            'today': get_hails_received(since=threshold),
            'three_months_ago': get_hails_received(since=threshold, until=three_months_ago),
            'six_months_ago': get_hails_received(since=threshold, until=six_months_ago),
            'twelve_months_ago': get_hails_received(since=threshold, until=twelve_months_ago),
        },
        'hails_total': {
            'current_year': get_hails_total(*current_year),
            'last_year': get_hails_total(*last_year),
        },
        'hails_average': {
            'last_three_months': get_hails_average(*last_three_months),
            'current_year': get_hails_average(*current_year),
            'last_year': get_hails_average(*last_year),
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
    area = request.args.get('area')
    insee = request.args.get('insee')

    def get_registered_groupements():
        query = User.query.join(
            User.roles
        ).outerjoin(
            Taxi  # needed for filtering on INSEE
        ).filter(
            Role.name == 'groupement'
        ).group_by(
            User.id,  # avoid a cartesian product
        )
        query = apply_filters_to_users(query, area, insee)
        return query.count()

    def get_fleet_data():
        Manager = aliased(User)
        query = db.session.query(
            User.id,
            User.email,
            User.fleet_size,
            func.Count(Taxi.id).label('count'),
            (func.Count(Taxi.id) * 100.0 / User.fleet_size).label('ratio'),
            func.Max(Taxi.added_at).label('last_taxi'),
            Manager.email.label('manager'),
        ).join(
            User.roles
        ).outerjoin(
            Taxi
        ).outerjoin(
            Manager, Manager.id == User.manager_id
        ).filter(
            Role.name == 'groupement'
        ).group_by(
            User.id,
            User.email,
            User.fleet_size,
            Manager.email,
        ).order_by(
            User.email
        )
        query = apply_filters_to_users(query, area, insee)
        return query

    schema = schemas.DataStatsGroupementsSchema()
    return schema.dump({'data': [{
        'registered_groupements': get_registered_groupements(),
        'fleet_data': get_fleet_data(),
    }]})
