import collections
import datetime
import functools
import json

from flask import Blueprint, request, current_app
from sqlalchemy import func, Text, DateTime, Numeric, or_, column
from sqlalchemy.orm import aliased
from sqlalchemy.dialects.postgresql import INTERVAL

from APITaxi_models2 import db, ADS, Departement, Role, Taxi, Town, User, Vehicle, VehicleDescription
from APITaxi_models2 import Conurbation
from APITaxi_models2.stats import stats_minute_insee, stats_hour_insee, StatsHails

from .. import schemas
from ..security import auth, current_user


blueprint = Blueprint('stats', __name__)
threshold = datetime.datetime(2022, 1, 1)


def interval(string):
    return func.cast(string, INTERVAL())


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
@auth.login_required(role=['admin'])
def stats_taxis():
    filters = get_filters()
    milestone_series = func.generate_series(
        func.now() - interval('1 year'),
        func.now(),
        interval('3 month'),
    ).alias('milestone')

    def get_registered_taxis(since=None):
        query = db.session.query(
            func.count(Taxi.id),
        ).select_from(
            milestone_series,
        ).join(
            Taxi, Taxi.added_at < column('milestone'),
        ).group_by(
            column('milestone'),
        ).order_by(
            column('milestone').desc(),
        )
        if since is not None:
            query = query.filter(Taxi.added_at >= since)
        query = apply_filters_to_taxis(query, *filters)

        today, three, six, _ignored, twelve = [int(count) for count, in query]

        return {
            'today': today,
            'three_months_ago': three,
            'six_months_ago': six,
            'twelve_months_ago': twelve,
        }

    def get_connected_taxis(since=None):
        query = db.session.query(
            func.count(Taxi.id),
        ).select_from(
            milestone_series,
        ).join(
            Taxi, Taxi.last_update_at < column('milestone')
        ).group_by(
            column('milestone'),
        ).order_by(
            column('milestone').desc(),
        )
        if since is not None:
            query = query.filter(Taxi.last_update_at >= since)
        query = apply_filters_to_taxis(query, *filters)

        today, three, six, _ignored, twelve = [int(count) for count, in query]

        return {
            'today': today,
            'three_months_ago': three,
            'six_months_ago': six,
            'twelve_months_ago': twelve,
        }

    def get_realtime_connected_taxis():
        query = db.session.query(
            func.sum(stats_minute_insee.value),
        ).filter(
            stats_minute_insee.time > func.now() - interval('1 minute')
        )
        query = apply_filters_to_stats_hour(query, *filters, model=stats_minute_insee)
        return query.scalar() or 0

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
        'registered_taxis': get_registered_taxis(),
        'connected_taxis': get_connected_taxis(),
        'registered_taxis_since_threshold': get_registered_taxis(since=threshold),
        'connected_taxis_since_threshold': get_connected_taxis(since=threshold),
        'connected_taxis_now': get_realtime_connected_taxis(),
        'monthly_hails_per_taxi': get_monthly_hails_per_taxi(),
        'average_radius': get_average_radius(),
        'average_radius_change': get_average_radius_change(),
        'connected_taxis_per_hour': get_connected_taxis_per_hour(threshold),
    }]})


@blueprint.route('/stats/hails', methods=['GET'])
@auth.login_required(role=['admin'])
def stats_hails():
    filters = get_filters()

    milestone_series = func.generate_series(
        func.now() - interval('1 year'),
        func.now(),
        interval('3 month'),
    ).alias('milestone')

    last_three_months = get_last_three_months_interval()
    current_year = get_current_year_interval()
    last_year = get_last_year_interval()

    def get_hails_received(since, status=None):
        query = db.session.query(
            func.count(StatsHails.id),
        ).select_from(
            milestone_series,
        ).join(
            StatsHails, StatsHails.added_at < column('milestone'),
        ).group_by(
            column('milestone'),
        ).order_by(
            column('milestone').desc(),
        )
        query = query.filter(StatsHails.added_at >= since)
        if status is not None:
            if status == 'timeout_taxi':
                query = query.filter(StatsHails.status == 'timeout_taxi', (StatsHails.timeout_taxi - StatsHails.received) < func.Cast('1 hour', INTERVAL()))
            elif status == 'timeout_ride':
                query = query.filter(StatsHails.status == 'timeout_taxi', (StatsHails.timeout_taxi - StatsHails.received) > func.Cast('1 hour', INTERVAL()))
            else:
                query = query.filter(StatsHails.status == status)
        query = apply_filters_to_hails(query, *filters)

        # Might be zero to five length
        result = list(query)
        today = int(result.pop(0)[0]) if result else 0
        three = int(result.pop(0)[0]) if result else 0
        six = int(result.pop(0)[0]) if result else 0
        _ignored = int(result.pop(0)[0]) if result else 0
        twelve = int(result.pop(0)[0]) if result else 0

        return {
            'today': today,
            'three_months_ago': three,
            'six_months_ago': six,
            'twelve_months_ago': twelve,
        }

    def get_hails_average_per(interval, since, until, status=None):
        counts = db.session.query(
            func.Count(StatsHails.id)
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
        'hails_received': get_hails_received(since=threshold),
        'hails_finished': get_hails_received(since=threshold, status='finished'),
        'hails_declined_by_taxi': get_hails_received(since=threshold, status='declined_by_taxi'),
        'hails_declined_by_customer': get_hails_received(since=threshold, status='declined_by_customer'),
        # When the taxi received but didn't reply
        'hails_timeout_taxi': get_hails_received(since=threshold, status='timeout_taxi'),
        # When the ride happened but didn't close
        'hails_timeout_ride': get_hails_received(since=threshold, status='timeout_ride'),
        'hails_timeout_customer': get_hails_received(since=threshold, status='timeout_customer'),
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
@auth.login_required(role=['admin'])
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
@auth.login_required(role=['admin'])
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
@auth.login_required(role=['admin'])
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
@auth.login_required(role=['admin'])
def stats_managers():
    # No search
    return _get_managers()


@blueprint.route('/stats/letaxi', methods=['GET'])
def stats_letaxi():
    def _get_user_count(role):
        query = db.session.query(User).join(User.roles).filter(Role.name == role)
        return query.count()

    def _get_taxis_connected(conurbations):
        # Get the number of taxis for each conurbation in the past months
        #        milestone        |    id    | count
        # ------------------------+----------+-------
        #  2022-04-01 00:00:00+00 | lyon     |   XXX
        taxis_count = db.session.query(
            column('milestone'),
            Conurbation.id,
            func.count(Taxi.id)
        ).select_from(
            func.generate_series(
                func.date_trunc('month', func.now() - func.cast('1 year', INTERVAL())),
                func.date_trunc('month', func.now()),
                func.cast('1 month', INTERVAL()),
            ).alias('milestone')
        ).join(
            Taxi, Taxi.added_at < column('milestone'),
        ).join(
            Taxi.ads,
        ).join(
            Conurbation, ADS.insee == func.any(Conurbation.members),
        ).filter(
            Conurbation.id.in_(conurbations),
        ).group_by(
            column('milestone'),
            Conurbation.id,
        ).order_by(
            column('milestone'),
        )

        # Use the expected number of taxis for each conurbation to compute a ratio
        taxis_connected = {}
        for milestone, conurbation_id, count in taxis_count:
            taxis_connected.setdefault(milestone, {})[conurbation_id] = round(100.0 * count / conurbations[conurbation_id], 2)

        return taxis_connected.items()

    def _get_hails_growth(conurbations):
        def _get_hails_count(when):
            query = db.session.query(
                Conurbation.id.label('conurbation_id'),
                func.count(StatsHails.id).label('count'),
            ).join(
                Conurbation, StatsHails.insee == func.any(Conurbation.members)
            ).filter(
                func.date_trunc('month', StatsHails.added_at) == func.date_trunc('month', when),
                Conurbation.id.in_(conurbations),
            ).group_by(
                'conurbation_id',
            ).order_by(
                'conurbation_id',
            )
            return query

        # Number of hails this past month
        this_month = dict(_get_hails_count(func.now() - func.cast('1 month', INTERVAL())))
        # Same question same month last year
        last_year = dict(_get_hails_count(func.now() - func.cast('1 year 1 month', INTERVAL())))

        # Group by conurbation
        hails_growth = {}
        for conurbation_id, count in this_month.items():
            hails_growth[conurbation_id] = 100.0 * (count - last_year[conurbation_id]) / last_year[conurbation_id]

        return hails_growth

    schema = schemas.PublicStatsSchema()
    return schema.dump({
        'groups': _get_user_count('groupement'),
        'apps': _get_user_count('editeur'),
        'taxis_connected': _get_taxis_connected({
            'lyon': 1417,  # Known ADS count from Mes ADS
            'grenoble': 213,
            'rouen': 301,
        }),
        'hails_growth': _get_hails_growth(['lyon']),
    })
