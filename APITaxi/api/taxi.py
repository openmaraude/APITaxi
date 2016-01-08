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
from shapely.geometry import Point
from sqlalchemy import distinct
from sqlalchemy.sql.expression import func as func_sql
from datetime import datetime, timedelta
from time import mktime, time
from functools import partial
from ..utils.validate_json import ValidatorMixin
from psycopg2.extras import RealDictCursor
import math
from itertools import islice
from collections import deque
from operator import itemgetter


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
    def wrapped(taxi, taxi_db):
        taxi_redis, distance, coords = taxi
        taxi_id = taxi_redis.id
        if not taxi_db[0]['taxi_ads_id']:
            current_app.logger.info('Taxi {} has no ADS'.format(taxi_id))
            return None
        zupc_id = taxi_db[0]['ads_zupc_id']
        if not any(map(lambda z: z.id ==zupc_id, zupc_customer)):
            current_app.logger.info('Taxi {} is not customer\'s zone'.format(taxi_id))
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
        characs = vehicle_models.VehicleDescription.get_characs(
                lambda o, f: o.get('vehicle_description_{}'.format(f)), t)
#Check if the taxi is operating in its ZUPC
        zupc = None
        for zupc in zupc_customer:
            if zupc.id == zupc_id:
                break
        if not zupc or not zupc.preped_geom.contains(Point(float(coords[1]), float(coords[0]))):
            current_app.logger.info('The taxi {} is not in his operating zone'.format(taxi_id))
            return None
        return {
            "id": taxi_id,
            "operator": t['u_email'],
            "position": {"lat": coords[0], "lon": coords[1]},
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
            "crowfly_distance": float(distance),
            "rating": 4.5,
            "status": taxi['vehicle_description_status']
        }
    return wrapped

@ns_taxis.route('/', endpoint="taxi_list")
class Taxis(Resource, ValidatorMixin):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument('lon', type=float, required=True, location='values')
    get_parser.add_argument('lat', type=float, required=True, location='values')
    get_parser.add_argument('favorite_operator', type=unicode, required=False,
            location='values')
    get_parser.add_argument('count', type=int, required=False,
            location='values', default=10)



    @login_required
    @roles_accepted('admin', 'moteur')
    @api.doc(responses={403:'You\'re not authorized to view it'},
            parser=get_parser, model=taxi_model)
    @json_mimetype_required
    def get(self):
        p = self.__class__.get_parser.parse_args()
        lon, lat = p['lon'], p['lat']
        if current_app.config['LIMITED_ZONE'] and\
            not Point(lon, lat).intersects(current_app.config['LIMITED_ZONE']):
            #It must be 403, but I don't know how our clients will react:
            return {'data': []}
        zupc_customer = index_zupc.intersection(lon, lat)
        if len(zupc_customer) == 0:
            current_app.logger.info('No zone found at {}, {}'.format(lat, lon))
            return {'data': []}
        r = redis_store.georadius(current_app.config['REDIS_GEOINDEX'], lat, lon)
        if len(r) == 0:
            current_app.logger.info('No taxi found at {}, {}'.format(lat, lon))
            return {'data': []}
        name_redis = '{}:{}:{}'.format(p['lon'], p['lat'], time())
        redis_store.zadd(name_redis, **dict([(id_, d) for id_, d, _ in r]))

        fresh_redis = 'fresh:'+name_redis
        nb_fresh_taxis = redis_store.zinterstore(fresh_redis,
                {name_redis:0, current_app.config['REDIS_TIMESTAMPS']:1}
        )
        if nb_fresh_taxis == 0:
            current_app.logger.info('No fresh taxi found at {}, {}'.format(lat, lon))
            return {'data': []}
        min_time = int(time()) - taxis_models.TaxiRedis._DISPONIBILITY_DURATION
        timestamps = dict(filter(lambda taxi_id_ts: taxi_id_ts[1]>= min_time,
            redis_store.zrange(fresh_redis, 0, -1, withscores=True)
            )
        )

        na_redis = 'na:'+name_redis
        r_not_available = redis_store.zinterstore(na_redis,
                {fresh_redis:0, current_app.config['REDIS_NOT_AVAILABLE']:0}
        )
        if r_not_available > 1:
            not_available = set(map(
                lambda taxi_id_operator: taxi_id_operator.split(':')[0],
                redis_store.zrange(na_redis, 0, -1)
            ))
            filter_fun = lambda taxi_id_operator, _:\
                taxi_id_operator.split(':')[0] not in not_available
            r = filter(filter_fun, r)

        zupc_customer = [administrative_models.ZUPC.cache.get(z) for z in zupc_customer]
        taxis_redis = dict()
        for taxi_id_operator, distance, coords in r:
            taxi_id, operator = taxi_id_operator.split(':')
            ts = timestamps[taxi_id_operator]
            if taxi_id not in taxis_redis:
                taxis_redis[taxi_id] = (taxis_models.TaxiRedis(taxi_id, []),
                    distance, coords)
            else:
                if all(map(lambda t: t[0].caracs['timestamps'] > ts,
                    taxis_redis[taxi_id].caracs)
                    ):
                    taxis_redis[taxi_id][1] = distance
                    taxis_redis[taxi_id][2] = coords
            taxis_redis[taxi_id][0]._caracs.append(
                (operator, {'timestamp': timestamps[taxi_id_operator],
                    'lat': coords[0], 'lon': coords[1], 'status': 'free'}
                )
            )
        taxis_redis = sorted(taxis_redis.values(), key=itemgetter(1))
        cur = db.session.connection().connection.cursor(cursor_factory=RealDictCursor)
        cur.execute(get_taxis_request, (tuple((t[0].id for t in taxis_redis)),))
        taxis_db = cur.fetchmany(4)
        taxis = []
        func_generate_taxis = generate_taxi_dict(zupc_customer,
                min_time, p['favorite_operator'])
        for t in taxis_redis:
            while len(taxis_db) == 0 or\
                    t[0].id == taxis_db[0]['taxi_id'] and t[0].id == taxis_db[-1]['taxi_id']:
                l = cur.fetchmany(4)
                if len(l) == 0:
                    break
                taxis_db.extend(l)
            if len(taxis_db) == 0:
                break
            #Get the first index that's not t[0].id
            index = next((i for i, v in enumerate(taxis_db) if v['taxi_id'] != t[0].id),
                    len(taxis_db))
            if taxis_db[0]['taxi_id'] != t[0].id :
                current_app.logger.info('Unable to find taxi {} in db'.format(t[0].id))
                continue
            gen = func_generate_taxis(t, taxis_db[:index])
            if gen:
                taxis.append(gen)
            del taxis_db[:index]
            if len(taxis) == p['count']:
                break

        taxis = sorted(taxis, key=lambda taxi: taxi['crowfly_distance'])
        #Clean-up redis
        redis_store.delete(fresh_redis, na_redis)
        return {'data': taxis}

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
            taxi = taxis_models.Taxi.query.get(taxi_json['id'])
        if not taxi:
            taxi = taxis_models.Taxi(driver=driver, vehicle=vehicle, ads=ads,
                    id=taxi_json.get('id', None))
        if 'status' in taxi_json:
            try:
                taxi.status = taxi_json['status']
            except AssertionError:
                abort(400, message='Invalid status')
        db.session.add(taxi)
        db.session.commit()
        return {'data':[taxi]}, 201

@ns_taxis.route('/_active', endpoint="taxis_active")
class ActiveTaxisRoute(Resource):

    @login_required
    @roles_accepted('admin', 'operateur')
    @api.doc(False)
    def get(self):
        frequencies = [f for f, _ in current_app.config['STORE_TAXIS_FREQUENCIES']]
        parser = reqparse.RequestParser()
        parser.add_argument('zupc', type=unicode, required=False, location='values')
        parser.add_argument('begin', type=float, required=False, location='values')
        parser.add_argument('end', type=float, required=False, location='values')
        parser.add_argument('operator', type=unicode, required=False, location='values')
        parser.add_argument('frequency',
            type=customFields.Integer(frequencies),
            required=False, location='values',
            default=frequencies[0])
        p = parser.parse_args()

        if not p['begin'] and not p['end']:
            p['end'] = int(time())
        view_window = (taxis_models.Taxi._ACTIVITY_TIMEOUT + p['frequency'] * 60)
        p['begin'] = p['begin'] or p['end'] - view_window
        p['end'] = p['end'] or p['begin'] + view_window

        filters = []
        if current_user.has_role('admin'):
            if p['operator']:
                filters.append("operator = {}".format(p['operator']))
        else:
            filters.append("operator = '{}'".format(current_user.email))

        if p['zupc']:
            z = db.session.query(func_sql.count(administrative_models.ZUPC.id)).first()
            if z == 0:
                abort(404, message="Unknown zupc")
            filters.append("zupc = '{}'".format(p['zupc']))
        filters.append('time >= {}s'.format(p['begin']))
        filters.append('time <= {}s'.format(p['end']))

        measurement_name = "nb_taxis_every_{}".format(p['frequency'])
        query = 'SELECT sum(value) FROM {} WHERE {} GROUP BY time({}m)'.format(
                measurement_name, " AND ".join(filters), p['frequency'])


        c = influx_db.get_client(current_app.config['INFLUXDB_TAXIS_DB'])
        data = []
        strptime = lambda d: datetime.strptime(d, '%Y-%m-%dT%H:%M:%SZ')
        current_app.logger.info('Query: {}'.format(query))
        for result_set in c.query(query):
            for v in result_set:
                data.append({
                  "x": int(mktime(strptime(v['time']).timetuple())),
                  "y": v['sum']
                  })
        return jsonify({"data": data})
