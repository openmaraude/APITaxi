# -*- coding: utf8 -*-
from flask_restful import Resource, reqparse
from flask.ext.restplus import fields
from flask.ext.security import login_required, current_user, roles_accepted
from flask import request, redirect, url_for, abort, jsonify
from ..models import taxis as taxis_models, administrative as administrative_models
from .. import db, api, redis_store, ns_taxis


@ns_taxis.route('/<int:taxi_id>/', endpoint="taxi_id")
class TaxiId(Resource):

    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @login_required
    @roles_accepted('admin', 'operateur')
    def get(self, taxi_id):
        taxi = taxis_models.Taxi.query.get(taxi_id)
#@TODO:gérer la relation operateur<->conducteur
        return taxi.as_dict()

taxi_details = api.model('taxi_details', taxis_models.Taxi.marshall_obj())
taxi_model = api.model('taxi', {"taxi": fields.Nested(taxi_details)})

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
    @login_required
    @roles_accepted('admin', 'operateur')
    @api.expect(taxi_model)
    def post(self):
        json = request.get_json()
        fields = ['immatriculation', 'numero_ads', 'insee', 'carte_pro', 'departement']
        if not json or\
            any(map(lambda f: f not in json, fields)):
            abort(400)
        departement = administrative_models.Departement.query\
            .filter_by(numero=str(json['departement'])).first()
        if not departement:
            abort(404)
        conducteur = taxis_models.Conducteur.query\
                .filter_by(carte_pro=json['carte_pro'],
                           departement_id=departement.id).first()
        if not conducteur:
            abort(404, {"error": "Unable to find carte_pro"})
        vehicle = taxis_models.Vehicle.query\
                .filter_by(immatriculation=json['immatriculation']).first()
        if not vehicle:
            abort(404, {"error": "Unable to find immatriculation"})
        ads = taxis_models.ADS.query\
                .filter_by(numero=json['numero_ads'], insee=json['insee']).first()
        if not ads:
            abort(404, {"error": "Unable to find numero_ads for this insee code"})
        taxi = taxis_models.Taxi.query.filter_by(conducteur_id=conducteur.id,
                vehicle_id=vehicle.id, ads_id=ads.id).first()
        if not taxi:
            taxi = taxis_models.Taxi()
            taxi.conducteur_id = conducteur.id
            taxi.vehicle_id = vehicle.id
            taxi.ads_id = ads.id
            db.session.add(taxi)
            db.session.commit()
        return redirect(url_for('taxi_id', taxi_id=taxi.id))
