# -*- coding: utf-8 -*-
import calendar, time
from flask.ext.restplus import fields, abort, marshal, Resource, reqparse
from flask.ext.security import login_required, current_user, roles_accepted
from flask import request, current_app
from APITaxi_models import (taxis as taxis_models, administrative as administrative_models)
from ..extensions import redis_store, index_zupc
from . import api
from ..descriptors.taxi import taxi_model, taxi_model_expect, taxi_put_expect
from APITaxi_utils.request_wants_json import json_mimetype_required
from shapely.geometry import Point
from time import time
import math
from itertools import groupby

ns_taxis = api.namespace('taxis', description="Taxi API")


@ns_taxis.route('/<string:taxi_id>/', endpoint="taxi_id")
class TaxiId(Resource):
    def get_descriptions(self, taxi_id):
        taxis = taxis_models.RawTaxi.get([taxi_id])
        if not taxis:
            abort(404, message='Unable to find taxi "{}"'.format(taxi_id))
        taxis = taxis[0]
        t = [t for t in taxis if current_user.id == t['vehicle_description_added_by']]
        if not t:
            abort(403, message='You\'re not authorized to view this taxi')
        v = redis_store.hget('taxi:{}'.format(taxi_id), current_user.email)
        return t, int(v.split(' ')[0]) if v else None

    @login_required
    @roles_accepted('admin', 'operateur')
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @json_mimetype_required
    def get(self, taxi_id):
        t, last_update_at = self.get_descriptions(taxi_id)
        taxi_m = marshal({'data':[
            taxis_models.RawTaxi.generate_dict(t,
            operator=current_user.email)]}, taxi_model)
        taxi_m['data'][0]['operator'] = current_user.email
        taxi_m['data'][0]['last_update'] = last_update_at
        return taxi_m

    @login_required
    @roles_accepted('admin', 'operateur')
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'}, model=taxi_model)
    @api.expect(taxi_put_expect, validate=True)
    @json_mimetype_required
    def put(self, taxi_id):
        hj = request.json
        t, last_update_at = self.get_descriptions(taxi_id)
        new_status = hj['data'][0]['status']
        if new_status != t[0]['vehicle_description_status']:
            cur = current_app.extensions['sqlalchemy'].db.session.\
                    connection().connection.cursor()
            cur.execute("UPDATE vehicle_description SET status=%s WHERE id=%s",
                    (new_status, t[0]['vehicle_description_id']))
            current_app.extensions['sqlalchemy'].db.session.commit()
            taxis_models.RawTaxi.flush(taxi_id)
            t[0]['vehicle_description_status'] = new_status
            taxi_id_operator = "{}:{}".format(taxi_id, current_user.email)
            if t[0]['vehicle_description_status'] == 'free':
                redis_store.srem(current_app.config['REDIS_NOT_AVAILABLE'],
                    taxi_id_operator)
            else:
                redis_store.sadd(current_app.config['REDIS_NOT_AVAILABLE'],
                    taxi_id_operator)

        taxi_m = marshal({'data':[
            taxis_models.RawTaxi.generate_dict(t, operator=current_user.email)]
            }, taxi_model)
        taxi_m['data'][0]['operator'] = current_user.email
        taxi_m['data'][0]['last_update'] = last_update_at
        return taxi_m


get_parser = reqparse.RequestParser()
get_parser.add_argument('lon', type=float, required=True, location='values')
get_parser.add_argument('lat', type=float, required=True, location='values')
get_parser.add_argument('favorite_operator', type=unicode, required=False,
    location='values')
get_parser.add_argument('count', type=int, required=False,
        location='values', default=10)

@ns_taxis.route('/', endpoint="taxi_list")
class Taxis(Resource):

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

    def filter_zone(self, t):
        zupc_id = t['ads_zupc_id']
        if not zupc_id in self.zupc_customer.keys():
            current_app.logger.debug('Taxi not in customer\'s zone')
            return False
        t_redis = self.taxis_redis[t['taxi_id']]
        if not self.zupc_customer[t['ads_zupc_id']].preped_geom.contains(
                      Point(float(t_redis.lon),
                          float(t_redis.lat))
                      ):
            current_app.logger.debug('Taxi is not in its zone')
            return False
        return True



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
            current_app.logger.debug('No zone found at {}, {}'.format(lat, lon))
            return {'data': []}
        #It returns a list of all taxis near the given point
        #For each taxi you have a tuple with: (id, distance, [lat, lon])
        positions = redis_store.georadius(current_app.config['REDIS_GEOINDEX'],
                lat, lon)
        if len(positions) == 0:
            current_app.logger.debug('No taxi found at {}, {}'.format(lat, lon))
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
            current_app.logger.debug('No fresh taxi found at {}, {}'.format(lat, lon))
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
#Sorting by distance
        sorted_ids = [t.id for t in
                sorted(self.taxis_redis.values(), key=lambda t: t.distance)]
        for i in range(0, int(math.ceil(len(sorted_ids)/float(p['count'])))):
            page_ids = sorted_ids[i*p['count']:(i+1)*p['count']]
            taxis_db = taxis_models.RawTaxi.get(page_ids)
            if len(taxis_db) == 0:
                continue
            l = [taxis_models.RawTaxi.generate_dict(t,
                        self.taxis_redis[t[0]['taxi_id']], min_time=min_time,
                        favorite_operator=p['favorite_operator'])
                for t in taxis_db if len(t) > 0
                if self.filter_zone(t[0])]
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
    @api.expect(taxi_model_expect, validate=True)
    @api.marshal_with(taxi_model)
    def post(self):
        hj = request.json
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
        current_app.extensions['sqlalchemy'].db.session.add(taxi)
        current_app.extensions['sqlalchemy'].db.session.commit()
        return {'data':[taxi]}, 201
