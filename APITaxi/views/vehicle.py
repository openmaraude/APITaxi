# -*- coding: utf8 -*-
from flask_restful import Resource, reqparse
from flask.ext.security import login_required, current_user, roles_accepted
from flask import request, redirect, url_for, abort, jsonify
from ..utils import create_obj_from_json
from ..models import taxis as taxis_models
from .. import db, api, ns_administrative
from flask.ext.restplus import fields
from ..utils.make_model import make_model


vehicle_model = make_model('taxis', 'Vehicle')
vehicle_expect = make_model('taxis', 'Vehicle', filter_id=True)
@ns_administrative.route('vehicles/', endpoint="vehicle")
class Vehicle(Resource):

    @login_required
    @roles_accepted('admin', 'operateur')
    @api.marshal_with(vehicle_model)
    @api.expect(vehicle_expect)
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    def post(self):
        json = request.get_json()
        if "data" not in json:
            abort(400)
        if len(json['data']) > 250:
            abort(413)
        new_vehicle = []
        for vehicle in json['data']:
            try:
                new_vehicle.append(create_obj_from_json(taxis_models.Vehicle, vehicle))
            except KeyError as e:
                print "Error :", e
                abort(400)
            db.session.add(new_vehicle[-1])
        db.session.commit()
        return {"data": new_vehicle}
