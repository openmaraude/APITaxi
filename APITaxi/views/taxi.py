# -*- coding: utf8 -*-
from flask_restful import Resource, reqparse
from flask.ext.restplus import fields, abort
from flask.ext.security import login_required, current_user, roles_accepted
from flask import request, redirect, url_for, jsonify
from ..models import taxis as taxis_models, administrative as administrative_models
from .. import db, api, redis_store, ns_taxis


taxi_model_details = api.model('taxi_model_details',
         {'vehicle_licence_plate': fields.String,
          'ads_numero': fields.Integer,
          'ads_insee': fields.String,
          'driver_professional_licence': fields.String,
          'driver_departement': fields.String,
           'id': fields.Integer})
taxi_model = api.model('taxi_model', {'data': fields.List(fields.Nested(taxi_model_details))})

@ns_taxis.route('/<int:taxi_id>/', endpoint="taxi_id")
class TaxiId(Resource):

    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @api.marshal_with(taxi_model)
    @login_required
    @roles_accepted('admin', 'operateur')
    def get(self, taxi_id):
        taxi = taxis_models.Taxi.query.get(taxi_id)
        return {'data': [taxi]}

    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @api.marshal_with(taxi_model)
    @api.expect(api.model('taxi_put_expect',
          {'data': fields.List(fields.Nested(api.model('api_expect_status',
                {'status': fields.String})))}))
    @login_required
    @roles_accepted('admin', 'operateur')
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
         {'vehicle_licence_plate': fields.String,
          'ads_numero': fields.Integer,
          'ads_insee': fields.String,
          'driver_professional_licence': fields.String,
          'driver_departement': fields.String
         }

@ns_taxis.route('/', endpoint="taxi_list")
class Taxis(Resource):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument('lon', type=float, required=True)
    get_parser.add_argument('lat', type=float, required=True)

    @api.doc(responses={403:'You\'re not authorized to view it'}, parser=get_parser)
    @login_required
    @roles_accepted('admin', 'moteur')
    def get(self):
        p = self.__class__.get_parser.parse_args()
        lon, lat = p['lon'], p['lat']

        r = redis_store.georadius('france', lat, lon)

        return {"taxis": map(lambda a: {"id":a[0], "distance": float(a[1]),
                               "lon":float(a[2][0]), "lat": float(a[2][1])}, r)}

    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @api.expect(api.model('taxi_expect',
                          {'data':fields.List(fields.Nested(
                              api.model('taxi_expect_details',
                                        dict_taxi_expect)))}))
    @login_required
    @roles_accepted('admin', 'operateur')
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
            .filter_by(numero=str(taxi_json['driver_departement'])).first()
        if not departement:
            abort(404, error='Unable to find the departement')
        driver = taxis_models.Driver.query\
                .filter_by(carte_pro=taxi_json['driver_professional_licence'],
                           departement_id=departement.id).first()
        if not driver:
            abort(404, {"error": "Unable to find carte_pro"})
        vehicle = taxis_models.Vehicle.query\
                .filter_by(immatriculation=taxi_json['vehicle_licence_plate']).first()
        if not vehicle:
            abort(404, {"error": "Unable to find immatriculation"})
        ads = taxis_models.ADS.query\
                .filter_by(numero=taxi_json['ads_numero'],
                           insee=taxi_json['ads_insee']).first()
        if not ads:
            abort(404, {"error": "Unable to find numero_ads for this insee code"})
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
