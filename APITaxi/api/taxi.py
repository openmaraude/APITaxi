# -*- coding: utf8 -*-
import calendar, time
from flask_restful import Resource, reqparse
from flask.ext.restplus import fields, abort, marshal
from flask.ext.security import login_required, current_user, roles_accepted
from flask import request, redirect, url_for, jsonify, current_app
from ..models import taxis as taxis_models, administrative as administrative_models
from .. import db, redis_store
from ..api import api

ns_taxis = api.namespace('taxis', description="Taxi API")

vehicle_descriptor = api.model('vehicle_descriptor',
    {
        "model": fields.String,
        "constructor": fields.String,
        "color": fields.String,
        "licence_plate": fields.String,
        "characteristics": fields.List(fields.String),
    })
coordinates_descriptor = api.model('coordinates_descriptor',
        {"lon": fields.Float, "lat": fields.Float})
ads_descriptor = api.model('ads_descriptor', {
        "numero": fields.String,
        "insee": fields.String
})
driver_descriptor = api.model('driver_descriptor', {
        'professional_licence': fields.String,
        'departement': fields.String(attribute='departement.numero')
})
taxi_descriptor = api.model('taxi_descriptor',
    {
        "id": fields.String,
        "operator": fields.String,
        "position": fields.Nested(coordinates_descriptor),
        "vehicle": fields.Nested(vehicle_descriptor),
        "last_update": fields.Integer,
        "crowfly_distance": fields.Float,
        "ads": fields.Nested(ads_descriptor),
        "driver": fields.Nested(driver_descriptor),
        "status": fields.String
    })

taxi_model_details = api.model('taxi_model_details',
         {'vehicle_licence_plate': fields.String,
          'ads_numero': fields.String,
          'ads_insee': fields.String,
          'driver_professional_licence': fields.String,
          'driver_departement': fields.String,
           'id': fields.String})
taxi_model = api.model('taxi_model', {'data': fields.List(fields.Nested(taxi_descriptor))})

@ns_taxis.route('/<string:taxi_id>/', endpoint="taxi_id")
class TaxiId(Resource):

    @login_required
    @roles_accepted('admin', 'operateur')
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    def get(self, taxi_id):
        taxi = taxis_models.Taxi.query.get(taxi_id)
        if not taxi:
            abort(404, message="Unable to find this taxi")
        taxi_m = marshal({'data':[taxi]}, taxi_model)
        taxi_m['data'][0]['operator'] = None
        return taxi_m

    @login_required
    @roles_accepted('admin', 'operateur')
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @api.marshal_with(taxi_model)
    @api.expect(api.model('taxi_put_expect',
          {'data': fields.List(fields.Nested(api.model('api_expect_status',
                {'status': fields.String})))}))
    def put(self, taxi_id):
        json = request.get_json()
        status = json['data'][0]['status']
        if status not in Taxi.__table__.columns.status.type.enums:
            abort(400)
        taxi = taxis_models.Taxi.query.get(taxi_id)
        taxi.status = status
        db.session.commit()
        return {'data': [taxi]}


dict_taxi_expect = \
         {'vehicle': fields.Nested(api.model('vehicle_expect', {'licence_plate': fields.String})),
          'ads': fields.Nested(api.model('ads_expect', {'numero': fields.String, 'insee': fields.String})),
          'driver': fields.Nested(api.model('driver_expect', {'professional_licence': fields.String,
                     'departement': fields.String}))
         }
@ns_taxis.route('/', endpoint="taxi_list")
class Taxis(Resource):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument('lon', type=float, required=True)
    get_parser.add_argument('lat', type=float, required=True)

    @login_required
    @roles_accepted('admin', 'moteur')
    @api.doc(responses={403:'You\'re not authorized to view it'}, parser=get_parser)
    @api.marshal_with(taxi_model)
    def get(self):
        p = self.__class__.get_parser.parse_args()
        lon, lat = p['lon'], p['lat']

        r = redis_store.georadius(current_app.config['REDIS_GEOINDEX'], lat, lon)
        taxis = []
        min_time = calendar.timegm(time.gmtime()) - 60*60
        for taxi_id, distance, coords in r:
            taxi_db = taxis_models.Taxi.query.get(taxi_id)
            if not taxi_db or taxi_db.status != 'free':
                continue
            operator, timestamp = taxi_db.operator(redis_store)
            if timestamp < min_time:
                continue
            taxis.append({
                "id": taxi_id,
                "operator": operator,
                "position": {"lat": coords[0], "lon": coords[1]},
                "vehicle": {
                        "model": taxi_db.vehicle.model,
                        "constructor": taxi_db.vehicle.constructor,
                        "color": taxi_db.vehicle.color,
                        "characteristics": taxi_db.vehicle.characteristics
                },
                "characteristics": taxi_db.vehicle.characteristics,
                "last_update": timestamp,
                "crowfly_distance": float(distance)
                })
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
    def post(self):
        json = request.get_json()
        if 'data' not in json:
            abort(400)
        if len(json['data']) > 1:
            abort(413)
        taxi_json = json['data'][0]
        if sorted(taxi_json.keys()) != sorted(dict_taxi_expect.keys()):
            abort(400)
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
            taxi.driver_id = driver.id
            taxi.vehicle_id = vehicle.id
            taxi.ads_id = ads.id
            db.session.add(taxi)
        db.session.commit()
        return redirect(url_for('taxi_id', taxi_id=taxi.id))
