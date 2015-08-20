# -*- coding: utf-8 -*-
import calendar, time
from flask.ext.restplus import fields, abort, marshal, Resource, reqparse
from flask.ext.security import login_required, current_user, roles_accepted
from flask import request, redirect, url_for, jsonify, current_app
from ..models import (taxis as taxis_models,
    administrative as administrative_models, stats as stats_models)
from ..extensions import (db, redis_store, index_zupc, user_datastore)
from ..api import api
from ..descriptors.taxi import taxi_model
from ..utils.request_wants_json import json_mimetype_required
from ..utils.cache_refresh import cache_refresh
from ..utils import arguments
from shapely.geometry import Point
from sqlalchemy import distinct
from sqlalchemy.sql.expression import func as func_sql
from datetime import datetime, timedelta
from time import mktime, time

ns_taxis = api.namespace('taxis', description="Taxi API")


@ns_taxis.route('/<string:taxi_id>/', endpoint="taxi_id")
class TaxiId(Resource):

    @login_required
    @roles_accepted('admin', 'operateur')
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @json_mimetype_required
    def get(self, taxi_id):
        taxi = taxis_models.Taxi.get(taxi_id)
        if not taxi:
            abort(404, message="Unable to find this taxi")
        operator = None
        for description in taxi.vehicle.descriptions:
            if description.added_by == current_user.id:
                operator = current_user
                break
        if not operator:
            abort(403, message="You're not authorized to view this taxi")
        taxi_m = marshal({'data':[taxi]}, taxi_model)
        taxi_m['data'][0]['operator'] = operator.email
        op, timestamp = taxi.get_operator(redis_store,
                favorite_operator=current_user.email)
        taxi_m['data'][0]['last_update'] = timestamp if op == current_user else None
        return taxi_m

    @login_required
    @roles_accepted('admin', 'operateur')
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @api.marshal_with(taxi_model)
    @api.expect(api.model('taxi_put_expect',
          {'data': fields.List(fields.Nested(api.model('api_expect_status',
                {'status': fields.String})))}))
    @json_mimetype_required
    def put(self, taxi_id):
        json = request.get_json()
        if 'data' not in json:
            abort(400, message="data is needed")
        if len(json['data']) != 1:
            abort(413, message="You can only PUT one taxi")
        if 'status' not in json['data'][0]:
            abort(400, message="a status is needed")
        status = json['data'][0]['status']
        if status == 'answering':
            abort(400, message='Setting status to answering is not authorized')
        taxi = taxis_models.Taxi.query.get(taxi_id)
        if current_user.id not in [desc.added_by for desc in taxi.vehicle.descriptions]:
            abort(403, message='You\'re not authorized to PUT this taxi')
        try:
            taxi.status = status
        except AssertionError as e:
            abort(400, message=str(e))

        cache_refresh(db.session(), [{'func': taxis_models.Taxi.get.refresh,
            'args': [taxis_models.Taxi, taxi_id]}])
        db.session.commit()
        #taxis_models.Taxi.get.refresh(taxis_models.Taxi, taxi_id)
        return {'data': [taxi]}


dict_taxi_expect = \
         {'vehicle': fields.Nested(api.model('vehicle_expect',
            {'licence_plate': fields.String})),
          'ads': fields.Nested(api.model('ads_expect',
              {'numero': fields.String, 'insee': fields.String})),
          'driver': fields.Nested(api.model('driver_expect',
              {'professional_licence': fields.String,
                'departement': fields.String})),
          'status': fields.String
         }

def generate_taxi_dict(zupc_customer, min_time, favorite_operator):
    def wrapped(taxi):
        taxi_id, distance, coords = taxi
        taxi_db = taxis_models.Taxi.get(taxi_id)
        if not taxi_db or not taxi_db.ads or not taxi_db.is_free(redis_store)\
            or taxi_db.ads.zupc_id not in zupc_customer:
            return None
        operator, timestamp = taxi_db.get_operator(redis_store,
                min_time, favorite_operator)
        if not operator:
            return None
#Check if the taxi is operating in its ZUPC
        if not Point(float(coords[1]), float(coords[0])).intersects(taxi_db.ads.zupc.geom):
            return None

        description = taxi_db.vehicle.get_description(operator)
        if not description:
            return None
        return {
            "id": taxi_id,
            "operator": operator.email,
            "position": {"lat": coords[0], "lon": coords[1]},
            "vehicle": {
                "model": description.model,
                "constructor": description.constructor,
                "color": description.color,
                "characteristics": description.characteristics,
                "licence_plate": taxi_db.vehicle.licence_plate,
                "nb_seats": description.nb_seats
            },
            "last_update": timestamp,
            "crowfly_distance": float(distance)
        }
    return wrapped


@ns_taxis.route('/', endpoint="taxi_list")
class Taxis(Resource):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument('lon', type=float, required=True, location='values')
    get_parser.add_argument('lat', type=float, required=True, location='values')
    get_parser.add_argument('favorite_operator', type=unicode, required=False, location='values')



    @login_required
    @roles_accepted('admin', 'moteur')
    @api.doc(responses={403:'You\'re not authorized to view it'}, parser=get_parser)
    @api.marshal_with(taxi_model)
    @json_mimetype_required
    def get(self):
        p = self.__class__.get_parser.parse_args()
        lon, lat = p['lon'], p['lat']
        zupc_customer = index_zupc.intersection(lon, lat)
        if len(zupc_customer) == 0:
            current_app.logger.info('No zone found at {}, {}'.format(lat, lon))
            return {'data': []}
        r = redis_store.georadius(current_app.config['REDIS_GEOINDEX'], lat, lon)
        if len(r) == 0:
            current_app.logger.info('No taxi found at {}, {}'.format(lat, lon))
            return {'data': []}
        min_time = int(time()) - 60*60
        favorite_operator = p['favorite_operator']
        taxis = filter(lambda t: t is not None,
                map(generate_taxi_dict(zupc_customer, min_time, favorite_operator), r))
        taxis = sorted(taxis, key=lambda taxi: taxi['crowfly_distance'])
        return {'data': taxis}

    @login_required
    @roles_accepted('admin', 'operateur')
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @api.expect(api.model('taxi_expect',
                          {'data':fields.List(fields.Nested(
                              api.model('taxi_expect_details',
                                        dict_taxi_expect)))}))
    @api.marshal_with(taxi_model)
    def post(self):
        json = request.get_json()
        if 'data' not in json:
            abort(400, message="data is required")
        if len(json['data']) > 1:
            abort(413, message="You can only post one taxi at a time")
        taxi_json = json['data'][0]
        if sorted(taxi_json.keys()) != sorted(dict_taxi_expect.keys()):
            abort(400, message="bad taxi description")
        departement = administrative_models.Departement.query\
            .filter_by(numero=str(taxi_json['driver']['departement'])).first()
        if not departement:
            abort(404, message='Unable to find the departement')
        driver = taxis_models.Driver.query\
                .filter_by(professional_licence=taxi_json['driver']['professional_licence'],
                           departement_id=departement.id).first()
        if not driver:
            abort(404, message="Unable to find the driver")
        vehicle = taxis_models.Vehicle.query\
                .filter_by(licence_plate=taxi_json['vehicle']['licence_plate']).first()
        if not vehicle:
            abort(404, message="Unable to find the licence plate")
        ads = taxis_models.ADS.query\
                .filter_by(numero=taxi_json['ads']['numero'],
                           insee=taxi_json['ads']['insee']).first()
        if not ads:
            abort(404, message="Unable to find numero_ads for this insee code")
        taxi = taxis_models.Taxi.query.filter_by(driver_id=driver.id,
                vehicle_id=vehicle.id, ads_id=ads.id).first()
        if not taxi:
            taxi = taxis_models.Taxi()
        taxi.driver = driver
        taxi.vehicle = vehicle
        taxi.ads = ads
        db.session.add(taxi)
        if 'status' in taxi_json:
            try:
                taxi.status = taxi_json['status']
            except AssertionError:
                abort(400, message='Invalid status')
        db.session.commit()
        return {'data':[taxi]}, 201

@ns_taxis.route('/_views', endpoint="taxi_active")
class ActiveTaxisRoute(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('zupc', type=int, required=False, location='values')
        parser.add_argument('operator', type=unicode, required=False, location='values')
        parser.add_argument('begin', type=float, required=False, location='values')
        parser.add_argument('end', type=float, required=False, location='values')
        parser.add_argument('granularity', type=arguments.Integer(15),
            location='values', default=15)
        p = parser.parse_args()

        if not p['begin'] and not p['end']:
            p['end'] = int(time())
        p['begin'] = p['begin'] or p['end'] - 15 * 60
        p['end'] = p['end'] or p['begin'] + 15 * 60

        filters = dict()

        if p['operator']:
            if not current_user.has_role('admin') and p['operator'] != current_user.email:
                abort(503)
            filters['operator_id'] = user_datastore.find_user(email=operator).id

        if p['zupc']:
            zupc = administrative_models.ZUPC.query.filter_by(insee=p['zupc']).first()
            if not zupc:
                abort(404, message='Unable to find a zupc for this insee code')
            filters['zupc_id'] = zupc.parent_id

        lower, upper = map(lambda k: datetime.fromtimestamp(p[k]), ['begin', 'end'])
        timestamp_sql = stats_models.ActiveTaxis.timestamp
        #Find upper bound in database
        max_ = db.session.query(func_sql.min(stats_models.ActiveTaxis.timestamp)).\
                    filter(timestamp_sql >= upper).first()[0]
        if not max_ or (max_ - upper) > timedelta(minutes=15):
            abort(404, message="Unable to find a timestamp for end")
        #Find lower bound in database
        opt = func_sql.max(timestamp_sql)
        min_ = db.session.query(func_sql.max(stats_models.ActiveTaxis.timestamp)).\
                    filter(timestamp_sql <= upper).first()[0]
        if not min_ or (lower - min_) > timedelta(minutes=15):
            abort(404, message="Unable to find a timestamp for begin")

        data = []
        t_attr = stats_models.ActiveTaxis.timestamp
        q = stats_models.ActiveTaxis.query.filter_by(**filters)
        q = q.filter(t_attr >= min_, t_attr <= max_)
        for v in q.all():
            bound = v.timestamp
            minute = (bound.minute/p.granularity) * p.granularity
            end = datetime(bound.year, bound.month, bound.day, bound.hour, minute)
            begin = end - timedelta(minutes=15)
            data.append(
                {
                    "operator": user_datastore.find_user(id=v.operator_id).email,
                    "zupc": administrative_models.ZUPC.query.get(v.zupc_id).insee,
                    "begin": mktime(begin.timetuple()),
                    "end": mktime(end.timetuple()),
                    "nb_taxis": v.nb_taxis
                }
            )
        return {"data": data}


