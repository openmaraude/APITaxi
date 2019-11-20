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
    def clean_taxis_timestamps():
        if redis_store.zcount(current_app.config['REDIS_TIMESTAMPS'], 0,
                  time() - models.TaxiRedis._DISPONIBILITY_DURATION) > 0:
            clean_geoindex_timestamps.apply()

    @staticmethod
    def get_page_taxis(positions_redis, zupc_customer, favorite_operator, page_size, page):
        #page_taxis is a dict. the key is an id of a taxi, the value is also a dict with info on this taxi
        #First we get the position of the taxis
        page_taxis = {
            v[0].decode(): {'distance': v[1]}
            for v in redis_store.zrangebyscore(positions_redis, 0., '+inf', page_size * page, page_size, True)
        }
        if len(page_taxis) == 0:
            return page_taxis
        #We add the position of each taxis
        for id_, pos in zip(page_taxis.keys(), redis_store.geopos(current_app.config['REDIS_GEOINDEX_ID'], *page_taxis.keys())):
            page_taxis[id_]['position'] = pos
        #Then we get information from the database for each taxi
        #If a taxi has several operators we'll have several descriptions, so we have a S at descriptions !
        for taxi in models.RawTaxi.get(page_taxis.keys()):
            page_taxis[taxi[0]['taxi_id']]['descriptions'] = taxi
        #If there's a bad id in redis, we now know it, so we can remove this taxi from the dict of taxis
        page_taxis = dict(filter(lambda t: 'descriptions' in t[1], page_taxis.items()))
        #We get all timestamps for each taxi, and each operator
        #We do it in a redis pipe, so we'll get all the results in a list
        #To deal with it we store in piped the position of each request
        pipe = redis_store.pipeline()
        pipe_count = 0
        for id_, values in page_taxis.items():
            for desc in values['descriptions']:
                pipe.zscore(current_app.config['REDIS_TIMESTAMPS'], desc['taxi_id'] + ':' + desc['u_email'])
                page_taxis[id_].setdefault('piped', []).append(pipe_count)
                pipe_count += 1
        timestamps = pipe.execute()
        #We iterate on taxis and get the timestamps
        for id_, taxi in page_taxis.items():
            page_taxis[id_]['timestamps'] = [timestamps[i] for i in taxi['piped']]

        #Filter of taxis that are not in the customer's zone or not in there zone
        #Generation of the response
        return [models.RawTaxi.generate_dict(t['descriptions'],
                    None, None,
                    favorite_operator=favorite_operator,
                    position={"lon": t['position'][0], "lat": t['position'][1]},
                    distance=t['distance'], timestamps=t['timestamps'])
            for t in page_taxis.values()
            if models.Taxi.is_in_zone(t['descriptions'], t['position'][0], t['position'][1], zupc_customer)
        ]

    @login_required
    @roles_accepted('admin', 'moteur')
    @api.doc(responses={403:'You\'re not authorized to view it'},
            parser=get_parser, model=taxi_model)
    @json_mimetype_required
    def get(self):
        """
        This function gets the taxi's zones of the position sent in the request.
        And then gets taxis around this position and filter them with the following rules:
         - Is the taxi available?
         - Is the position fresh enough?
         - Can this taxi operate here?
        Then it will gets some information from the database.
        The taxis will be ordered by growing distance from the request's position
        """
        p = get_parser.parse_args()
        t = time()
        lon, lat = p['lon'], p['lat']
        zupc_customer = models.ZUPC.get(lon, lat)
        if not zupc_customer:
            return {'data': []}
        max_distance = models.ZUPC.get_max_distance(zupc_customer)
        self.clean_taxis_timestamps()
        positions_redis = '{}:{}:{}'.format(lon, lat, t)
        if models.TaxiRedis.store_positions(lon, lat, max_distance, t, redis_store, positions_redis) == 0:
            return {'data': []}
        models.TaxiRedis.remove_not_available(lon, lat, positions_redis, max_distance, redis_store)
        taxis = []
        page = 0
        page_size = p['count'] * 4
        while len(taxis) < p['count']:
            page_taxis = self.get_page_taxis(positions_redis, zupc_customer, p['favorite_operator'], page_size, page)
            if len(page_taxis) == 0:
                break
            page += 1
            taxis.extend([_f for _f in page_taxis if _f])
        
        taxis = sorted(taxis[:p['count']], key=lambda t: t['crowfly_distance'])
        influx_db.write_get_taxis(zupc_customer[0].insee, lon, lat, current_user.email, request, len(taxis))

        return {'data': taxis}

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
