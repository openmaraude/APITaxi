import collections
import datetime
import functools
import json

from flask import Blueprint, request, current_app
from flask_security import current_user, login_required, roles_accepted
from sqlalchemy import func, Text, DateTime, Numeric, or_
from sqlalchemy.orm import aliased
from sqlalchemy.dialects.postgresql import JSONB, INTERVAL

from APITaxi_models2 import db, ADS, Departement, Role, Taxi, Town, User, Vehicle, VehicleDescription
from APITaxi_models2.stats import stats_minute_insee, stats_hour_insee, StatsHails

from .. import schemas


blueprint = Blueprint('stats', __name__)
threshold = datetime.datetime(2022, 1, 1)


def get_filters():
    departements = request.args.get('departements')
    if departements:
        departements = departements.split(',')
    
    insee_codes = request.args.get('insee')
    if insee_codes:
        insee_codes = insee_codes.split(',')
    
    groups = request.args.get('groups')
    if groups:
        groups = groups.split(',')

    manager = request.args.get('manager')
    if manager:
        manager = int(manager)

    return departements, insee_codes, groups, manager


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


def apply_filters_to_taxis(query, departements, insee_codes, groups, manager):
    if departements or insee_codes:
        query = query.join(Taxi.ads)
        if departements:
            query = query.filter(or_(*(
                func.substr(ADS.insee, 0, 3) == dpt for dpt in departements
            )))
        if insee_codes:
            query = query.filter(ADS.insee.in_(insee_codes))
    if groups:
        query = query.filter(Taxi.added_by_id.in_(groups))
    if manager:
        query = query.join(Taxi.added_by).filter(User.manager_id == manager)
    return query


def apply_filters_to_stats_hour(query, departements, insee_codes, groups, manager, model=stats_hour_insee):
    if departements:
        query = query.filter(or_(*(
            func.substr(model.insee, 0, 3) == dpt for dpt in departements
        )))
    if insee_codes:
        query = query.filter(model.insee.in_(insee_codes))
    if groups or manager:
        # TODO
        return query.filter(False)
    return query


def apply_filters_to_hails(query, departements, insee_codes, groups, manager):
    if departements:
        query = query.filter(or_(*(
            func.substr(StatsHails.insee, 0, 3) == dpt for dpt in departements
        )))
    if insee_codes:
        query = query.filter(StatsHails.insee.in_(insee_codes))
    if groups or manager:
        query = query.join(User, User.email == StatsHails.operateur)
        if groups:
            query = query.filter(User.id.in_(groups))
        if manager:
            query = query.filter(User.manager_id == manager)
    return query


@blueprint.route('/stats/taxis', methods=['GET'])
@login_required
@roles_accepted('admin')
def stats_taxis():
    filters = get_filters()
    three_months_ago, six_months_ago, twelve_months_ago = get_intervals()

    def get_registered_taxis(since=None, until=None):
        query = Taxi.query
        if since is not None:
            query = query.filter(Taxi.added_at >= since)
        if until is not None:
            query = query.filter(Taxi.added_at < until)
        query = apply_filters_to_taxis(query, *filters)
        return query.count()

    def get_connected_taxis(since=None, until=None):
        query = Taxi.query.filter(Taxi.last_update_at.isnot(None))
        if since is not None:
            query = query.filter(Taxi.last_update_at >= since)
        if until is not None:
            query = query.filter(Taxi.last_update_at < until)
        query = apply_filters_to_taxis(query, *filters)
        return query.count()

    def get_realtime_connected_taxis():
        query = stats_minute_insee.query
        query = apply_filters_to_stats_hour(query, *filters, model=stats_minute_insee)
        return query.count()

    def get_monthly_hails_per_taxi():
        counts = db.session.query(
            func.Count(StatsHails.id)
        ).select_from(Taxi).outerjoin(
            StatsHails, StatsHails.taxi_hash == func.encode(func.digest(Taxi.id, 'sha1'), 'hex')
        ).group_by(Taxi.id)
        counts = apply_filters_to_taxis(counts, *filters)
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
        query = apply_filters_to_taxis(query, *filters)
        return query.scalar()

    def get_average_radius_change():
        query = db.session.query(
            func.Count(VehicleDescription.radius) * 100.0 / func.Nullif(func.Count(), 0)
        ).join(Taxi.vehicle).join(Vehicle.descriptions)
        query = apply_filters_to_taxis(query, *filters)
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
        counts = apply_filters_to_stats_hour(counts, *filters).subquery()
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
        'connected_taxis_now': get_realtime_connected_taxis(),
        'monthly_hails_per_taxi': get_monthly_hails_per_taxi(),
        'average_radius': get_average_radius(),
        'average_radius_change': get_average_radius_change(),
        'connected_taxis_per_hour': get_connected_taxis_per_hour(threshold),
    }]})


@blueprint.route('/stats/hails', methods=['GET'])
@login_required
@roles_accepted('admin')
def stats_hails():
    filters = get_filters()
    three_months_ago, six_months_ago, twelve_months_ago = get_intervals()
    last_three_months = get_last_three_months_interval()
    current_year = get_current_year_interval()
    last_year = get_last_year_interval()

    def get_hails_received(since, until=None, status=None):
        query = StatsHails.query
        if since is not None:
            query = query.filter(StatsHails.added_at >= since)
        if until is not None:
            query = query.filter(StatsHails.added_at < until)
        if status is not None:
            if status == 'timeout_taxi':
                query = query.filter(StatsHails.status == 'timeout_taxi', (StatsHails.timeout_taxi - StatsHails.received) < func.Cast('1 hour', INTERVAL()))
            elif status == 'timeout_ride':
                query = query.filter(StatsHails.status == 'timeout_taxi', (StatsHails.timeout_taxi - StatsHails.received) > func.Cast('1 hour', INTERVAL()))
            else:
                query = query.filter(StatsHails.status == status)
        query = apply_filters_to_hails(query, *filters)
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
        counts = apply_filters_to_hails(counts, *filters)
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
        query = apply_filters_to_hails(query, *filters)

        return query

    schema = schemas.DataStatsHailsSchema()
    return schema.dump({'data': [{
        'hails_received': {
            'today': get_hails_received(since=threshold),
            'three_months_ago': get_hails_received(since=threshold, until=three_months_ago),
            'six_months_ago': get_hails_received(since=threshold, until=six_months_ago),
            'twelve_months_ago': get_hails_received(since=threshold, until=twelve_months_ago),
        },
        'hails_finished': {
            'today': get_hails_received(since=threshold, status='finished'),
            'three_months_ago': get_hails_received(since=threshold, until=three_months_ago, status='finished'),
            'six_months_ago': get_hails_received(since=threshold, until=six_months_ago, status='finished'),
            'twelve_months_ago': get_hails_received(since=threshold, until=twelve_months_ago, status='finished'),
        },
        'hails_declined_by_taxi': {
            'today': get_hails_received(since=threshold, status='declined_by_taxi'),
            'three_months_ago': get_hails_received(since=threshold, until=three_months_ago, status='declined_by_taxi'),
            'six_months_ago': get_hails_received(since=threshold, until=six_months_ago, status='declined_by_taxi'),
            'twelve_months_ago': get_hails_received(since=threshold, until=twelve_months_ago, status='declined_by_taxi'),
        },
        'hails_declined_by_customer': {
            'today': get_hails_received(since=threshold, status='declined_by_customer'),
            'three_months_ago': get_hails_received(since=threshold, until=three_months_ago, status='declined_by_customer'),
            'six_months_ago': get_hails_received(since=threshold, until=six_months_ago, status='declined_by_customer'),
            'twelve_months_ago': get_hails_received(since=threshold, until=twelve_months_ago, status='declined_by_customer'),
        },
        'hails_timeout_taxi': {  # When the taxi received but didn't reply
            'today': get_hails_received(since=threshold, status='timeout_taxi'),
            'three_months_ago': get_hails_received(since=threshold, until=three_months_ago, status='timeout_taxi'),
            'six_months_ago': get_hails_received(since=threshold, until=six_months_ago, status='timeout_taxi'),
            'twelve_months_ago': get_hails_received(since=threshold, until=twelve_months_ago, status='timeout_taxi'),
        },
        'hails_timeout_ride': {  # When the ride happened but didn't close
            'today': get_hails_received(since=threshold, status='timeout_ride'),
            'three_months_ago': get_hails_received(since=threshold, until=three_months_ago, status='timeout_ride'),
            'six_months_ago': get_hails_received(since=threshold, until=six_months_ago, status='timeout_ride'),
            'twelve_months_ago': get_hails_received(since=threshold, until=twelve_months_ago, status='timeout_ride'),
        },
        'hails_timeout_customer': {
            'today': get_hails_received(since=threshold, status='timeout_customer'),
            'three_months_ago': get_hails_received(since=threshold, until=three_months_ago, status='timeout_customer'),
            'six_months_ago': get_hails_received(since=threshold, until=six_months_ago, status='timeout_customer'),
            'twelve_months_ago': get_hails_received(since=threshold, until=twelve_months_ago, status='timeout_customer'),
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
    filters = get_filters()

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
        query = apply_filters_to_taxis(query, *filters)
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
        query = apply_filters_to_taxis(query, *filters)
        return query

    schema = schemas.DataStatsGroupementsSchema()
    return schema.dump({'data': [{
        'registered_groupements': get_registered_groupements(),
        'fleet_data': get_fleet_data(),
    }]})


@blueprint.route('/stats/adsmap', methods=['GET'])
@login_required
@roles_accepted('admin')
def stats_adsmap():
    filters = get_filters()

    def get_registered_taxis():
        query = db.session.query(
            func.Count(Taxi.id),
            Departement.numero,
            Departement.nom,
            func.ST_AsGeoJSON(func.ST_PointOnSurface(func.ST_Collect(func.Geometry(Town.shape)))),
        ).join(
            Taxi.ads
        ).join(
            Town, Town.insee == ADS.insee
        ).join(
            Departement, Departement.numero == func.substr(ADS.insee, 0 , 3)
        ).group_by(
            Departement.numero,
            Departement.nom,
        ).order_by(
            Departement.numero,
        )
        query = apply_filters_to_taxis(query, *filters)
        return query

    schema = schemas.DataStatsADSmapSchema()
    return schema.dump({'data': [{
        'count': taxis[0],
        'insee': taxis[1],
        'name': taxis[2],
        'position': json.loads(taxis[3]),
    } for taxis in get_registered_taxis()]})


@functools.lru_cache()
def _get_groups(search):
    query = db.session.query(
        User.id,
        User.email,
        User.commercial_name,
    ).join(
        User.roles
    ).filter(
        Role.name == 'groupement'
    ).order_by(
        User.email,
    )
    if search:
        query = query.filter(
            or_(
                User.email.ilike(f'%{search}%'),
                User.commercial_name.ilike(f'%{search}%'),
            )
        )

    schema = schemas.DataGroupSchema()
    return schema.dump({'data': query})


@blueprint.route('/stats/groups', methods=['GET'])
@login_required
@roles_accepted('admin')
def stats_groups():
    search = request.args.get('search')
    return _get_groups(search)


@functools.lru_cache()
def _get_managers():
    query = db.session.query(
        User.id,
        User.email,
        User.commercial_name,
    ).filter(
        User.id.in_(db.session.query(User.manager_id))
    ).order_by(
        User.email
    )

    schema = schemas.DataGroupSchema()
    return schema.dump({'data': query})


@blueprint.route('/stats/managers', methods=['GET'])
@login_required
@roles_accepted('admin')
def stats_managers():
    # No search
    return _get_managers()
