import collections
import datetime
import json

from flask import Blueprint, request, current_app
from flask_security import current_user, login_required, roles_accepted
from sqlalchemy import func, Text, DateTime, Numeric
from sqlalchemy.dialects.postgresql import JSONB

from APITaxi_models2 import db, ADS, ArchivedHail, Hail, Role, Taxi, User, Vehicle, VehicleDescription
from APITaxi_models2.stats import stats_hour_insee

from .. import schemas


LYON_METROPOLE = ('69123', '69003', '69029', '69033', '69034', '69040', '69044', '69046', '69271', '69063', '69273', '69068', '69069', '69071', '69072', '69275', '69081', '69276', '69085', '69087', '69088', '69089', '69278', '69091', '69096', '69100', '69279', '69116', '69117', '69127', '69282', '69283', '69284', '69142', '69143', '69149', '69152', '69153', '69163', '69286', '69168', '69191', '69194', '69202', '69199', '69204', '69205', '69207', '69290', '69233', '69292', '69293', '69296', '69244', '69250', '69256', '69259', '69260', '69266')
ROUEN_METROPOLE = ('76540', '76005', '76020', '76039', '76056', '76069', '76088', '76095', '76108', '76103', '76116', '76131', '76157', '76165', '76178', '76212', '76216', '76222', '76231', '76237', '76273', '76475', '76282', '76313', '76319', '76322', '76350', '76354', '76366', '76367', '76377', '76378', '76391', '76402', '76410', '76429', '76436', '76451', '76448', '76457', '76464', '76474', '76484', '76486', '76497', '76498', '76513', '76514', '76536', '76550', '76558', '76560', '76561', '76575', '76591', '76599', '76614', '76617', '76631', '76634', '76636', '76640', '76608', '76681', '76682', '76705', '76709', '76717', '76750', '76753', '76759')

blueprint = Blueprint('stats', __name__)
threshold = datetime.datetime(2022, 1, 1)


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


def apply_area_to_taxis(query, area):
    if area:
        query = query.join(Taxi.ads)
        if area == 'lyon':
            query = query.filter(ADS.insee.in_(LYON_METROPOLE))
        elif area == 'rouen':
            query = query.filter(ADS.insee.in_(ROUEN_METROPOLE))
    return query


def apply_area_to_stats(query, area):
    if area:
        if area == 'lyon':
            query = query.filter(stats_hour_insee.insee.in_(LYON_METROPOLE))
        elif area == 'rouen':
            query = query.filter(stats_hour_insee.insee.in_(ROUEN_METROPOLE))
    return query


def apply_area_to_hails(query, area, archived=False):
    if area:
        if archived:
            if area == 'lyon':
                query = query.filter(ArchivedHail.insee.in_(LYON_METROPOLE))
            elif area == 'rouen':
                query = query.filter(ArchivedHail.insee.in_(ROUEN_METROPOLE))
        else:
            query = query.join(Hail.taxi)
            query = apply_area_to_taxis(query, area)
    return query


def apply_area_to_users(query, area):
    if area:
        query = query.join(Taxi.ads)
        if area == 'lyon':
            query = query.filter(ADS.insee.in_(LYON_METROPOLE))
        elif area == 'rouen':
            query = query.filter(ADS.insee.in_(ROUEN_METROPOLE))
    return query


@blueprint.route('/stats/taxis', methods=['GET'])
@login_required
@roles_accepted('admin')
def stats_taxis():
    three_months_ago, six_months_ago, twelve_months_ago = get_intervals()
    area = request.args.get('area')

    def get_registered_taxis(since=None, until=None):
        query = Taxi.query
        if since:
            query = query.filter(Taxi.added_at >= since)
        if until:
            query = query.filter(Taxi.added_at < until)
        query = apply_area_to_taxis(query, area)
        return query.count()

    def get_connected_taxis(since=None, until=None):
        query = Taxi.query.filter(Taxi.last_update_at.isnot(None))
        if since:
            query = query.filter(Taxi.last_update_at >= since)
        if until:
            query = query.filter(Taxi.last_update_at < until)
        query = apply_area_to_taxis(query, area)
        return query.count()

    def get_monthly_hails_per_taxi():
        counts = db.session.query(
            func.Count(Hail.id)
        ).select_from(Taxi).outerjoin(
            Hail, Hail.taxi_id == Taxi.id
        ).group_by(Taxi.id)
        counts = apply_area_to_taxis(counts, area)        
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
        query = apply_area_to_taxis(query, area)
        return query.scalar()

    def get_average_radius_change():
        query = db.session.query(
            func.Count(VehicleDescription.radius) * 100.0 / func.Nullif(func.Count(), 0)
        ).join(Taxi.vehicle).join(Vehicle.descriptions)
        query = apply_area_to_taxis(query, area)
        return query.scalar()

    def get_connected_taxis_per_hour(since=None):
        # First "rebuild" stats_hour from stats_hour_insee
        counts = db.session.query(
            func.date_trunc('hour', stats_hour_insee.time).label('trunc'),
            func.Sum(stats_hour_insee.value)
        ).group_by(
            'trunc',
        )
        if since:
            counts = counts.filter(stats_hour_insee.time >= since)
        counts = apply_area_to_stats(counts, area).subquery()
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

    def get_hails_received(since=None, until=None):
        def _get_hails_received(model):
            query = model.query
            if query:
                query = query.filter(model.added_at >= since)
            if until:
                query = query.filter(model.added_at < until)
            query = apply_area_to_hails(query, area, archived=model == ArchivedHail)
            return query.count()
        return _get_hails_received(Hail) + _get_hails_received(ArchivedHail)

    def get_hails_average_per(interval, since, until, status=None):
        def _get_hails_average(model):
            counts = db.session.query(
                func.Count()
            ).filter(
                model.added_at >= since,
                model.added_at < until,
            ).group_by(
                func.date_trunc(interval, model.added_at)
            )
            if status:
                counts = counts.filter(model.status == status)
            counts = apply_area_to_hails(counts, area, archived=model==ArchivedHail)
            counts = counts.subquery()
            query = db.session.query(func.Avg(counts.c.count))
            return query.scalar() or 0
        return _get_hails_average(Hail) + _get_hails_average(ArchivedHail)

    def get_average_transition_time(from_status, to_status):
        from_status = json.dumps({"status": from_status})
        to_status = json.dumps({"status": to_status})
        transition_logs = db.session.query(
            # Having to cast transition_log to JSBON, json_path_query doesn't exist (should we convert transition_log to begin with?)
            # then having to cast to Text because Postgres can't cast from JSONB to TIMESTAMP
            # There is a datetime() function for path queries, but it doesn't recognize our ISO format, where the regular timestamp does
            func.jsonb_path_query(Hail.transition_log.cast(JSONB()), '$[*] ? (@.to_status == $status).timestamp', to_status).cast(Text()).label('to_status'),
            func.jsonb_path_query(Hail.transition_log.cast(JSONB()), '$[*] ? (@.to_status == $status).timestamp', from_status).cast(Text()).label('from_status'),
        )
        transition_logs = apply_area_to_hails(transition_logs, area)
        transition_logs = transition_logs.subquery()
        intervals = db.session.query(
            (transition_logs.c.to_status.cast(DateTime()) - transition_logs.c.from_status.cast(DateTime())).label('interval')
        ).filter(
            transition_logs.c.to_status.isnot(None)
        ).subquery()
        average = db.session.query(func.Avg(intervals.c.interval))
        return (average.scalar() or datetime.timedelta()).total_seconds()

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
        def _get_hails_total(model):
            query = db.session.query(
                func.date_part('month', model.added_at).label('month'),
                func.count(),
            ).filter(
                model.added_at >= since,
                model.added_at < until
            ).group_by('month').order_by('month')
            query = apply_area_to_hails(query, area, archived=model == ArchivedHail)
            return query

        counter = collections.Counter(dict(_get_hails_total(ArchivedHail)))
        counter.update(dict(_get_hails_total(Hail)))
        return list(counter.items())

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
        query = apply_area_to_users(query, area)
        return query.count()

    def get_fleet_data():
        query = db.session.query(
            User.id,
            User.email,
            User.fleet_size,
            func.Count(Taxi.id).label('count'),
            (func.Count(Taxi.id) * 100.0 / User.fleet_size).label('ratio'),
            func.Max(Taxi.added_at).label('last_taxi')
        ).join(
            User.roles
        ).outerjoin(
            Taxi
        ).filter(
            Role.name == 'groupement'
        ).group_by(
            User.id,
            User.email,
            User.fleet_size,
        ).order_by(
            User.email
        )
        query = apply_area_to_users(query, area)
        return query

    schema = schemas.DataStatsGroupementsSchema()
    return schema.dump({'data': [{
        'registered_groupements': get_registered_groupements(),
        'fleet_data': get_fleet_data(),
    }]})
