# -*- coding: utf-8 -*-
import calendar, time
from flask.ext.restplus import fields, abort, marshal, Resource, reqparse
from flask.ext.security import login_required, current_user, roles_accepted
from flask import request, redirect, url_for, jsonify, current_app
from ..models import (taxis as taxis_models, vehicle as vehicle_models,
    administrative as administrative_models)
from ..extensions import (db, redis_store, index_zupc, user_datastore)
from ..api import api
from ..descriptors.taxi import taxi_model, taxi_model_expect, taxi_put_expect
from ..utils.request_wants_json import json_mimetype_required
from ..utils import arguments
from ..utils import influx_db
from ..utils import fields as customFields
from ..utils.caching import cache_in
from shapely.geometry import Point
from sqlalchemy import distinct
from sqlalchemy.sql.expression import func as func_sql
from datetime import datetime, timedelta
from time import mktime, time
from functools import partial
from ..utils.validate_json import ValidatorMixin
import math
from itertools import islice, groupby
from collections import deque


ns_taxis = api.namespace('taxis', description="Taxi API")


@ns_taxis.route('/<string:taxi_id>/', endpoint="taxi_id")
class TaxiId(Resource, ValidatorMixin):

    @login_required
    @roles_accepted('admin', 'operateur')
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @json_mimetype_required
    def get(self, taxi_id):
        taxi = taxis_models.Taxi.cache.get(taxi_id)
        if not taxi:
            abort(404, message="Unable to find this taxi")
        description = taxi.vehicle.description
        if not description:
            abort(403, message="You're not authorized to view this taxi")
        taxi_m = marshal({'data':[taxi]}, taxi_model)
        taxi_m['data'][0]['operator'] = current_user.email
        v = redis_store.hget('taxi:{}'.format(taxi_id), current_user.email)
        if v:
            taxi_m['data'][0]['last_update'] = int(v.split(' ')[0])
        else:
            taxi_m['data'][0]['last_update'] = None
        return taxi_m

    @login_required
    @roles_accepted('admin', 'operateur')
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @api.marshal_with(taxi_model)
    @api.expect(taxi_put_expect)
    @json_mimetype_required
    def put(self, taxi_id):
        taxi = taxis_models.Taxi.cache.get(taxi_id)
        if not taxi:
            abort(404, message='Unable to find taxi "{}"'.format(taxi_id))
        if current_user.id not in [desc.added_by for desc in taxi.vehicle.descriptions]:
            abort(403, message='You\'re not authorized to PUT this taxi')

        hj = request.json
        self.validate(hj)
        new_status = hj['data'][0]['status']
        if new_status != taxi.status:
            try:
                taxi.vehicle.description.status = hj['data'][0]['status']
            except AssertionError as e:
                abort(400, message=str(e))
            db.session.add(taxi.vehicle.description)
            db.session.commit()
            taxi.cache.flush(taxi.cache._cache_key(taxi.id))
        return {'data': [taxi]}


get_columns_names = lambda m: [c.name for c in m.__table__.columns]
fields_get_taxi = fields = {
    "taxi": get_columns_names(taxis_models.Taxi),
    "model": get_columns_names(vehicle_models.Model),
    "constructor": get_columns_names(vehicle_models.Constructor),
    "vehicle_description": get_columns_names(vehicle_models.VehicleDescription),
    "vehicle": get_columns_names(vehicle_models.Vehicle),
    '"ADS"': get_columns_names(taxis_models.ADS),
    "driver": get_columns_names(taxis_models.Driver),
    "departement": get_columns_names(administrative_models.Departement),
    "u": ['email']
}

get_taxis_request = """SELECT {} FROM taxi
LEFT OUTER JOIN vehicle ON vehicle.id = taxi.vehicle_id
LEFT OUTER JOIN vehicle_description ON vehicle.id = vehicle_description.vehicle_id
LEFT OUTER JOIN model ON model.id = vehicle_description.model_id
LEFT OUTER JOIN constructor ON constructor.id = vehicle_description.constructor_id
LEFT OUTER JOIN "ADS" ON "ADS".id = taxi.ads_id
LEFT OUTER JOIN driver ON driver.id = taxi.driver_id
LEFT OUTER JOIN departement ON departement.id = driver.departement_id
LEFT OUTER JOIN "user" AS u ON u.id = vehicle_description.added_by
WHERE taxi.id IN %s ORDER BY taxi.id""".format(", ".join(
    [", ".join(["{0}.{1} AS {2}_{1}".format(k, v2, k.replace('"', '')) for v2 in v])
        for k, v  in fields_get_taxi.items()])
    )



def generate_taxi_dict(zupc_customer, min_time, favorite_operator):
    def wrapped(taxi_redis, taxi_db):
        taxi_id = taxi_redis.id
        if not taxi_db[0]['taxi_ads_id']:
            current_app.logger.info('Taxi {} has no ADS'.format(taxi_id))
            return None
        operator, timestamp = taxi_redis.get_operator(min_time, favorite_operator)
        if not operator:
            current_app.logger.info('Unable to find operator for taxi {}'.format(taxi_id))
            return None
        taxi = None
        for t in taxi_db:
            if t['u_email'] == operator:
                taxi = t
                break
        if not taxi:
            return None
        if taxi['ads_zupc_id'] not in zupc_customer:
            current_app.logger.info('Taxi not in customer\'s zone')
            return
        if not zupc_customer[taxi['ads_zupc_id']].preped_geom.contains(
                      Point(float(taxi_redis.lon),
                          float(taxi_redis.lat))
                      ):
            current_app.logger.info('Taxi is not in its zone')
            return
        characs = vehicle_models.VehicleDescription.get_characs(
                lambda o, f: o.get('vehicle_description_{}'.format(f)), t)
        return {
            "id": taxi_id,
            "operator": t['u_email'],
            "position": taxi_redis.coords,
            "vehicle": {
                "model": taxi['model_name'],
                "constructor": taxi['constructor_name'],
                    "color": taxi['vehicle_description_color'],
                    "characteristics": characs,
                "nb_seats": taxi['vehicle_description_nb_seats'],
                "licence_plate": taxi['vehicle_licence_plate'],
            },
            "ads": {
                "insee": taxi['ads_insee'],
                "numero": taxi['ads_numero']
            },
            "driver": {
                "departement": taxi['departement_numero'],
                "professional_licence": taxi['driver_professional_licence']
            },
            "last_update": timestamp,
            "crowfly_distance": float(taxi_redis.distance),
            "rating": 4.5,
            "status": taxi['vehicle_description_status']
        }
    return wrapped

get_parser = reqparse.RequestParser()
get_parser.add_argument('lon', type=float, required=True, location='values')
get_parser.add_argument('lat', type=float, required=True, location='values')
get_parser.add_argument('favorite_operator', type=unicode, required=False,
    location='values')
get_parser.add_argument('count', type=int, required=False,
        location='values', default=10)

@ns_taxis.route('/', endpoint="taxi_list")
class Taxis(Resource, ValidatorMixin):

    def filter_not_available(self, fresh_redis, na_redis):
        #As said before there might be non-fresh taxis
        nb_not_available = redis_store.zinterstore(na_redis,
                {fresh_redis:0, current_app.config['REDIS_NOT_AVAILABLE']:0}
        )
        if nb_not_available == 0:
            return
        for v in redis_store.zrange(na_redis, 0, -1):
            try:
                del self.taxis_redis[v.split(':')[0]]
            except KeyError:
                pass

    @login_required
    @roles_accepted('admin', 'moteur')
    @api.doc(responses={403:'You\'re not authorized to view it'},
            parser=get_parser, model=taxi_model)
    @json_mimetype_required
    def get(self):
        p = get_parser.parse_args()
        lon, lat = p['lon'], p['lat']
        if current_app.config['LIMITED_ZONE'] and\
            not Point(lon, lat).intersects(current_app.config['LIMITED_ZONE']):
            #It must be 403, but I don't know how our clients will react:
            return {'data': []}
        self.zupc_customer = index_zupc.intersection(lon, lat)
        if len(self.zupc_customer) == 0:
            current_app.logger.info('No zone found at {}, {}'.format(lat, lon))
            return {'data': []}
        #It returns a list of all taxis near the given point
        #For each taxi you have a tuple with: (id, distance, [lat, lon])
        positions = redis_store.georadius(current_app.config['REDIS_GEOINDEX'],
                lat, lon)
        if len(positions) == 0:
            current_app.logger.info('No taxi found at {}, {}'.format(lat, lon))
            return {'data': []}
        name_redis = '{}:{}:{}'.format(lon, lat, time())
        redis_store.zadd(name_redis, **{id_: d for id_, d, _ in positions})
        #The resulting set may contain unfresh taxi because they haven't be
        #deleted yet
        fresh_redis = 'fresh:'+name_redis
        nb_fresh_taxis = redis_store.zinterstore(fresh_redis,
                {name_redis:0, current_app.config['REDIS_TIMESTAMPS']:1}
        )
        if nb_fresh_taxis == 0:
            current_app.logger.info('No fresh taxi found at {}, {}'.format(lat, lon))
            return {'data': []}
        min_time = int(time()) - taxis_models.TaxiRedis._DISPONIBILITY_DURATION
        #We select only the fresh taxis
        timestamps = dict(redis_store.zrangebyscore(fresh_redis, min_time,
            '+inf', withscores=True))

        #Select only fresh taxis, and add operator and timestamps to the tuple
        positions = [(v[0], [v[1], v[2], timestamps[v[0]]])
                        for v in positions if v[0] in timestamps]
        self.taxis_redis = {k: taxis_models.TaxiRedis(k, caracs_list=list(v))
            for k, v in groupby(positions, key=lambda k_v: k_v[0].split(':')[0])}
        na_redis = 'na:'+name_redis
        self.filter_not_available(fresh_redis, na_redis)

        self.zupc_customer = {id_: administrative_models.ZUPC.cache.get(id_)
                            for id_ in self.zupc_customer}

        taxis = []
        func_generate_taxis = generate_taxi_dict(self.zupc_customer,
                min_time, p['favorite_operator'])
#Sorting by distance
        sorted_ids = [t.id for t in
                sorted(self.taxis_redis.values(), key=lambda t: t.distance)]
        for i in range(0, int(math.ceil(len(sorted_ids)/float(p['count'])))):
            page_ids = sorted_ids[i*p['count']:(i+1)*p['count']]
            taxis_db = [v for v in cache_in(get_taxis_request, page_ids,
                'taxis_cache_sql', get_id=lambda v: v[0]['taxi_id'],
                   transform_result=lambda r: map(lambda v: list(v[1]),
                                 groupby(r, lambda t: t['taxi_id']),))
                   if v]
            if len(taxis_db) == 0:
                continue
            l = [func_generate_taxis(self.taxis_redis[t[0]['taxi_id']], t)
                    for t in taxis_db if len(t) > 0]
            taxis.extend(filter(None, l))
            if len(taxis) >= p['count']:
                break
        #Clean-up redis
        redis_store.delete(fresh_redis, na_redis, name_redis)
        return {'data': sorted(taxis, key=lambda t: t['crowfly_distance'])[:p['count']]}

    @login_required
    @roles_accepted('admin', 'operateur')
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @api.expect(taxi_model_expect)
    @api.marshal_with(taxi_model)
    def post(self):
        hj = request.json
        self.validate(hj)
        taxi_json = hj['data'][0]
        departement = administrative_models.Departement.filter_by_or_404(
            numero=str(taxi_json['driver']['departement']))
        driver = taxis_models.Driver.filter_by_or_404(
                professional_licence=taxi_json['driver']['professional_licence'],
                           departement_id=departement.id)
        vehicle = taxis_models.Vehicle.filter_by_or_404(
                licence_plate=taxi_json['vehicle']['licence_plate'])
        ads = taxis_models.ADS.filter_by_or_404(
              numero=taxi_json['ads']['numero'],insee=taxi_json['ads']['insee'])
        taxi = taxis_models.Taxi.query.filter_by(driver_id=driver.id,
                vehicle_id=vehicle.id, ads_id=ads.id).first()
        if taxi_json.get('id', None):
            if current_user.has_role('admin'):
                taxi = taxis_models.Taxi.query.get(taxi_json['id'])
            else:
                del taxi_json['id']
        if not taxi:
            taxi = taxis_models.Taxi(driver=driver, vehicle=vehicle, ads=ads,
                    id=taxi_json.get('id', None))
        #This can happen if this is posted with a admin user
        if 'status' in taxi_json and taxi.vehicle.description:
            try:
                taxi.status = taxi_json['status']
            except AssertionError:
                abort(400, message='Invalid status')
        db.session.add(taxi)
        db.session.commit()
        return {'data':[taxi]}, 201
