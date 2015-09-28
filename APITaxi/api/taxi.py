# -*- coding: utf-8 -*-
import calendar, time
from flask.ext.restplus import fields, abort, marshal, Resource, reqparse
from flask.ext.security import login_required, current_user, roles_accepted
from flask import request, redirect, url_for, jsonify, current_app
from ..models import (taxis as taxis_models,
    administrative as administrative_models)
from ..extensions import (db, redis_store, index_zupc, user_datastore)
from ..api import api
from ..descriptors.taxi import taxi_model, taxi_model_expect, taxi_put_expect
from ..utils.request_wants_json import json_mimetype_required
from ..utils.cache_refresh import cache_refresh
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

ns_taxis = api.namespace('taxis', description="Taxi API")


@ns_taxis.route('/<string:taxi_id>/', endpoint="taxi_id")
class TaxiId(Resource, ValidatorMixin):

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
        op, timestamp = taxi.get_operator(favorite_operator=current_user.email)
        taxi_m['data'][0]['last_update'] = timestamp if op == current_user else None
        return taxi_m

    @login_required
    @roles_accepted('admin', 'operateur')
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @api.marshal_with(taxi_model)
    @api.expect(taxi_put_expect)
    @json_mimetype_required
    def put(self, taxi_id):
        taxi = taxis_models.Taxi.query.get(taxi_id)
        if not taxi:
            abort(404, message='Unable to find taxi "{}"'.format(taxi_id))
        if current_user.id not in [desc.added_by for desc in taxi.vehicle.descriptions]:
            abort(403, message='You\'re not authorized to PUT this taxi')

        hj = request.json
        self.validate(hj)
        try:
            taxi.status = hj['data'][0]['status']
        except AssertionError as e:
            abort(400, message=str(e))

        cache_refresh(db.session(), {'func': taxis_models.Taxi.getter_db.refresh,
            'args': [taxis_models.Taxi, taxi_id]})
        db.session.commit()
        return {'data': [taxi]}



def generate_taxi_dict(zupc_customer, min_time, favorite_operator):
    def wrapped(taxi):
        taxi_id, distance, coords = taxi
        taxi_db = taxis_models.Taxi.get(taxi_id)
        if not taxi_db or not taxi_db.ads or not taxi_db.is_free()\
            or taxi_db.ads.zupc_id not in zupc_customer:
            return None
        operator, timestamp = taxi_db.get_operator(min_time, favorite_operator)
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
class Taxis(Resource, ValidatorMixin):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument('lon', type=float, required=True, location='values')
    get_parser.add_argument('lat', type=float, required=True, location='values')
    get_parser.add_argument('favorite_operator', type=unicode, required=False,
            location='values')

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
        min_time = int(time()) - taxis_models.Taxi._ACTIVITY_TIMEOUT
        favorite_operator = p['favorite_operator']
        taxis = filter(lambda t: t is not None,
                map(generate_taxi_dict(zupc_customer, min_time, favorite_operator), r))
        taxis = sorted(taxis, key=lambda taxi: taxi['crowfly_distance'])
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
        if not taxi:
            taxi = taxis_models.Taxi(driver=driver, vehicle=vehicle, ads=ads)
        if 'status' in taxi_json:
            try:
                taxi.status = taxi_json['status']
            except AssertionError:
                abort(400, message='Invalid status')
        db.session.commit()
        return {'data':[taxi]}, 201

@ns_taxis.route('/_active', endpoint="taxis_active")
class ActiveTaxisRoute(Resource):

    @login_required
    @roles_accepted('admin', 'operateur')
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
