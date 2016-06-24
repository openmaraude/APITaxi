# -*- coding: utf-8 -*-
import calendar, time
from flask.ext.restplus import fields, abort, marshal, Resource, reqparse
from flask.ext.security import login_required, current_user, roles_accepted
from flask import request, current_app, g
from APITaxi_models import (taxis as taxis_models, administrative as administrative_models)
from APITaxi_utils.caching import cache_single, cache_in
from ..extensions import redis_store
from . import api
from ..descriptors.taxi import taxi_model, taxi_model_expect, taxi_put_expect
from APITaxi_utils.request_wants_json import json_mimetype_required
from shapely.geometry import Point
from time import time
from datetime import datetime, timedelta
import math
from itertools import groupby, compress, izip, islice
from shapely.prepared import prep
from shapely.wkb import loads as load_wkb

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
        if new_status != t[0]['vehicle_description_status'] or\
                t[0]['taxi_last_update_at'] is None or\
                t[0]['taxi_last_update_at'] <= (datetime.now() - timedelta(hours=4)):
            cur = current_app.extensions['sqlalchemy'].db.session.\
                    connection().connection.cursor()
            cur.execute("UPDATE vehicle_description SET status=%s WHERE id=%s",
                           (new_status, t[0]['vehicle_description_id'])
            )
            cur.execute("UPDATE taxi set last_update_at = %s WHERE id = %s",
                    (datetime.now(), t[0]['taxi_id'])
            )
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
    def filter_zone(self, taxi, p):
        if not taxi:
            current_app.logger.debug('Taxi {} not fount in db')
            return False
        taxi = taxi[0]
        zupc_id = taxi['ads_zupc_id']
        if not zupc_id in self.zupc_customer.keys():
            current_app.logger.debug('Taxi {} not in customer\'s zone'.format(
                taxi.get('taxi_id', 'no id')))
            return False
        if not self.zupc_customer[self.parent_zupc[zupc_id]].contains(
                        Point(float(p[1]), float(p[0]))):
            current_app.logger.debug('Taxi {} is not in its zone'.format(
                taxi.get('taxi_id', 'no id')))
            return False
        return True

    def set_not_available(self, lon, lat, name_redis):
        store_key = name_redis+'_operateur'
        redis_store.georadius(current_app.config['REDIS_GEOINDEX'], lat, lon,
                              storedistkey=store_key)
        redis_store.zinterstore(store_key, [store_key,
                                current_app.config['REDIS_TIMESTAMPS'],
                                current_app.config['REDIS_NOT_AVAILABLE']])
        self.not_available = {t[0].split(':')[0] for t
                              in redis_store.zscan_iter(store_key)}

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
        self.zupc_customer = cache_single("""SELECT id, parent_id FROM "ZUPC"
                            WHERE ST_INTERSECTS(shape, 'POINT(%s %s)');""",
                            (lon, lat), "zupc_lon_lat",
                            lambda v: (v['id'], v['parent_id']),
                            get_id=lambda a:(float(a[1].split(",")[0][1:].strip()),
                                             float(a[1].split(",")[1][:-1].strip())))
        if len(self.zupc_customer) == 0:
            current_app.logger.debug('No zone found at {}, {}'.format(lat, lon))
            return {'data': []}
        g.keys_to_delete = []
        name_redis = '{}:{}:{}'.format(lon, lat, time())
        g.keys_to_delete.append(name_redis)
        #It returns a list of all taxis near the given point
        #For each taxi you have a tuple with: (id, distance, [lat, lon])
        nb_positions = redis_store.georadius(current_app.config['REDIS_GEOINDEX_ID'],
                lat, lon, storedistkey=name_redis)
        if nb_positions == 0:
            current_app.logger.debug('No taxi found at {}, {}'.format(lat, lon))
            return {'data': []}
        self.parent_zupc = {r[0]: r[1] for r in self.zupc_customer}
        self.zupc_customer = {r[0]: r[1]
          for r in cache_in(
              'SELECT id, ST_AsBinary(shape) AS shape FROM "ZUPC" WHERE id in %s',
               {int(r1[1]) for r1 in self.zupc_customer}, "zupc_parent_shape",
               lambda v: (v['id'], prep(load_wkb(bytes(v['shape'])))),
              get_id=lambda v:unicode(v[0]))}
        taxis = []
        offset = 0
        count = p['count'] * 4
        self.set_not_available(lon, lat, name_redis)
        while len(taxis) < p['count']:
            page_ids_distances = [v for v in redis_store.zrangebyscore(name_redis, 0., '+inf',
                                    offset, count, True) if v[0] not in self.not_available]
            offset += count
            if len(page_ids_distances) == 0:
                break
            page_ids = [v[0] for v in page_ids_distances]
            distances = [v[1] for v in page_ids_distances]
            positions = redis_store.geopos(current_app.config['REDIS_GEOINDEX_ID']
                                           ,*page_ids)
            taxis_db = taxis_models.RawTaxi.get(page_ids)
#We get all timestamps
            pipe = redis_store.pipeline()
            map(lambda l_taxis:map(
                lambda t: pipe.zscore(current_app.config['REDIS_TIMESTAMPS'],
                                      t['taxi_id']+':'+t['u_email']),l_taxis)
                , taxis_db)
            timestamps = pipe.execute()
#If we have taxis_db = [{t_1}, {}, {t_21, t_22}, {t_3}]
#Then we want timestamps_slices = [(0, 1), (1, 1), (1, 3), (3, 4)]
            timestamps_slices = []
            map(lambda i: timestamps_slices.append((0, len(i)))\
                if not timestamps_slices\
                else timestamps_slices.append((timestamps_slices[-1][1],
                                               timestamps_slices[-1][1]+len(i))),
                taxis_db)

            l = [taxis_models.RawTaxi.generate_dict(t[0],
                        None, None,
                        favorite_operator=p['favorite_operator'],
                        position={"lon": t[1][0], "lat": t[1]},
                        distance=t[2], timestamps=islice(timestamps, *t[3]))
                for t in izip(taxis_db, positions, distances, timestamps_slices) if len(t) > 0
                if self.filter_zone(t[0], t[1])]
            taxis.extend(filter(None, l))
        return {'data': sorted(taxis, key=lambda t: t['crowfly_distance'])[:p['count']]}

    @login_required
    @roles_accepted('admin', 'operateur')
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @api.expect(taxi_model_expect, validate=True)
    @api.marshal_with(taxi_model)
    def post(self):
        db = current_app.extensions['sqlalchemy'].db
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
        db.session.add(taxi)
        db.session.commit()
        return {'data':[taxi]}, 201
