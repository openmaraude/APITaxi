# -*- coding: utf-8 -*-
import calendar, time, hashlib, math
from flask_restplus import fields, abort, marshal, Resource, reqparse
from flask_security import login_required, current_user, roles_accepted
from flask import request, current_app, g
import APITaxi_models as models
from APITaxi_models import db
from APITaxi_utils import influx_db
from APITaxi_utils.reqparse import DataJSONParser
from ..extensions import redis_store
from . import api
from ..descriptors.taxi import taxi_model, taxi_model_expect, taxi_put_expect
from ..tasks import clean_geoindex_timestamps
from APITaxi_utils.request_wants_json import json_mimetype_required
from shapely.geometry import Point
from time import time
from datetime import datetime, timedelta
from itertools import groupby, compress, islice
from shapely.prepared import prep
from shapely.wkb import loads as load_wkb
from sqlalchemy.sql.expression import text

ns_taxis = api.namespace('taxis', description="Taxi API")


@ns_taxis.route('/<string:taxi_id>/', endpoint="taxi_id")
class TaxiId(Resource):
    def get_descriptions(self, taxi_id):
        taxis = models.RawTaxi.get([taxi_id])
        if not taxis:
            abort(404, message='Unable to find taxi "{}"'.format(taxi_id))
        taxis = taxis[0]
        t = [t for t in taxis if current_user.id == t['vehicle_description_added_by']]
        if not t:
            abort(403, message='You\'re not authorized to view this taxi')
        v = redis_store.hget('taxi:{}'.format(taxi_id).encode(), current_user.email)
        return t, int(v.decode().split(' ')[0]) if v else None

    @login_required
    @roles_accepted('admin', 'operateur')
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @json_mimetype_required
    def get(self, taxi_id):
        t, last_update_at = self.get_descriptions(taxi_id)
        taxi_m = marshal({'data':[
            models.RawTaxi.generate_dict(t,
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
        parser = DataJSONParser()
        t, last_update_at = self.get_descriptions(taxi_id)
        new_status = parser.get_data()[0]['status']
        if new_status != t[0]['vehicle_description_status'] or\
                t[0]['taxi_last_update_at'] is None or\
                t[0]['taxi_last_update_at'] <= (datetime.now() - timedelta(hours=4)):
            cur = current_app.extensions['sqlalchemy'].db.session.\
                    connection().connection.cursor()
            cur.execute("UPDATE vehicle_description SET status=%s WHERE id=%s",
                           (new_status, t[0]['vehicle_description_id'])
            )
            to_set = ['last_update_at = %s', [datetime.now()]]
            if t[0]['taxi_current_hail_id']:
                hail = models.Hail.query.from_statement(
                    text("SELECT * from hail where id=:hail_id")
                ).params(hail_id=t[0]['taxi_current_hail_id']).one()
                hail_status, current_hail_id = models.Taxi.get_new_hail_status(
                    hail.id, new_status, hail._status)
                if hail_status:
                    hail.status = hail_status
                    to_set[0] += ", current_hail_id = %s"
                    to_set[1].append(current_hail_id)
                current_app.extensions['sqlalchemy'].db.session.add(hail)
            query = "UPDATE taxi SET {} WHERE id = %s".format(to_set[0])
            cur.execute(query, (to_set[1] + [t[0]['taxi_id']]))
            current_app.extensions['sqlalchemy'].db.session.commit()
            t[0]['vehicle_description_status'] = new_status
            taxi_id_operator = "{}:{}".format(taxi_id, current_user.email)
            if t[0]['vehicle_description_status'] == 'free':
                redis_store.zrem(current_app.config['REDIS_NOT_AVAILABLE'],
                    taxi_id_operator)
            else:
                redis_store.zadd(current_app.config['REDIS_NOT_AVAILABLE'],
                                 {taxi_id_operator: 0.})
            current_app.extensions['redis_saved'].zadd(
                'taxi_status:{}'.format(taxi_id),
                {'{}_{}'.format(new_status, time()): float(time())}
            )

        taxi_m = marshal({'data':[
            models.RawTaxi.generate_dict(t, operator=current_user.email)]
            }, taxi_model)
        taxi_m['data'][0]['operator'] = current_user.email
        taxi_m['data'][0]['last_update'] = last_update_at
        return taxi_m


get_parser = reqparse.RequestParser()
get_parser.add_argument('lon', type=float, required=True, location='values')
get_parser.add_argument('lat', type=float, required=True, location='values')
get_parser.add_argument('favorite_operator', type=str, required=False,
    location='values')
get_parser.add_argument('count', type=int, required=False,
        location='values', default=10)

@ns_taxis.route('/', endpoint="taxi_list")
class Taxis(Resource):

    @staticmethod
    def check_freshness():
        if redis_store.zcount(current_app.config['REDIS_TIMESTAMPS'], 0,
                  time() - models.TaxiRedis._DISPONIBILITY_DURATION) > 0:
            clean_geoindex_timestamps.apply()

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
        self.zupc_customer = db.session.execute(
            """SELECT id, parent_id, max_distance, insee
               FROM "ZUPC"
               WHERE ST_INTERSECTS(shape, 'POINT(:lon :lat)')
               AND parent_id = id
               ORDER BY max_distance ASC;""", {"lon": lon, "lat": lat}
        ).fetchall()
        if len(self.zupc_customer) == 0:
            current_app.logger.debug('No zone found at {}, {}'.format(lat, lon))
            return {'data': []}
        zupc_insee = self.zupc_customer[0][3]
        max_distance = models.ZUPC.get_max_distance(self.zupc_customer)
        self.check_freshness()
        g.keys_to_delete = []
        name_redis = '{}:{}:{}'.format(lon, lat, time())
        g.keys_to_delete.append(name_redis)
        #It returns a list of all taxis near the given point
        #For each taxi you have a tuple with: (id, distance, [lat, lon])
        nb_positions = redis_store.georadius(current_app.config['REDIS_GEOINDEX_ID'],
                lon, lat, radius=max_distance, unit='m', store_dist=name_redis)
        if nb_positions == 0:
            current_app.logger.debug('No taxi found at {}, {}'.format(lat, lon))
            return {'data': []}
        self.parent_zupc = {r[0]: r[1] for r in self.zupc_customer}
        self.zupc_customer = {r[0]: r[1]
          for r in  [(v[0], prep(load_wkb(bytes(v[1])))) for v in db.session.execute(
              'SELECT id, ST_AsBinary(shape) AS shape FROM "ZUPC" WHERE id in :zupc_list',
              {"zupc_list": tuple((int(r1[1]) for r1 in self.zupc_customer))}).fetchall()]}
        taxis = []
        offset = 0
        count = p['count'] * 4
        store_key = name_redis+'_operateur'
        g.keys_to_delete.append(store_key)
        self.not_available = models.TaxiRedis.not_available_ids(lon, lat, name_redis, max_distance, store_key)
        while len(taxis) < p['count']:
            page_ids_distances = [v for v in redis_store.zrangebyscore(name_redis, 0., '+inf',
                                    offset, count, True) if v[0].decode() not in self.not_available]
            offset += count
            if len(page_ids_distances) == 0:
                break
            page_ids = [v[0].decode() for v in page_ids_distances]
            distances = [v[1] for v in page_ids_distances]
            positions = redis_store.geopos(current_app.config['REDIS_GEOINDEX_ID']
                                           ,*page_ids)
            taxis_db = models.RawTaxi.get(page_ids)
#We get all timestamps
            pipe = redis_store.pipeline()
            list(map(lambda l_taxis:[pipe.zscore(current_app.config['REDIS_TIMESTAMPS'],
                                      t['taxi_id']+':'+t['u_email']) for t in l_taxis]
                , taxis_db))
            timestamps = pipe.execute()
#For each member of timestamp_slices we have the first index of the first element
#in timestamp, and the index of the last element
#If we have taxis_db = [{t_1,}, {,}, {t_21, t_22}, {t_3,}]
#Then we want timestamps_slices = [(0, 1), (1, 1), (1, 3), (3, 4)]
            timestamps_slices = []
            list(map(lambda i: timestamps_slices.append((0, len(i)))\
                if not timestamps_slices\
                else timestamps_slices.append((timestamps_slices[-1][1],
                                               timestamps_slices[-1][1]+len(i))),
                taxis_db))
            l = [models.RawTaxi.generate_dict(t[0],
                        None, None,
                        favorite_operator=p['favorite_operator'],
                        position={"lon": t[1][0], "lat": t[1][1]},
                        distance=t[2], timestamps=islice(timestamps, *t[3]))
                for t in zip(taxis_db, positions, distances, timestamps_slices) if len(t) > 0
                if models.Taxi.is_in_zone(t[0], t[1][0], t[1][1], self.zupc_customer, self.parent_zupc)]
            taxis.extend([_f for _f in l if _f])

        influx_db.write_point(current_app.config['INFLUXDB_TAXIS_DB'],
                             "get_taxis_requests",
                             {
                                 "zupc": zupc_insee,
                                 "position": "{:.3f}:{:.3f}".format(float(lon), float(lat)),
                                 "moteur": current_user.email,
                                 "customer": hashlib.sha224(
                                     str(
                                         (
                                            request.headers.getlist("X-Forwarded-For")[0].rpartition(' ')[-1]
                                            if 'X-Forwarded-For' in request.headers
                                            else request.remote_addr
                                         ) or 'untrackable'
                                        ).encode('utf-8')
                                 ).hexdigest()[:10]
                             },
                              value=len(taxis)
        )
        return {'data': sorted(taxis, key=lambda t: t['crowfly_distance'])[:p['count']]}

    @login_required
    @roles_accepted('admin', 'operateur')
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @api.expect(taxi_model_expect, validate=True)
    @api.marshal_with(taxi_model)
    def post(self):
        db = current_app.extensions['sqlalchemy'].db
        parser = DataJSONParser(filter_=taxi_model_expect)
        taxi_json = parser.get_data()[0]
        if not current_user.has_role('admin') and "id" in taxi_json:
            del taxi_json['id']
        taxi = models.Taxi(**taxi_json)
        db.session.add(taxi)
        db.session.commit()
        return {'data':[taxi]}, 201
