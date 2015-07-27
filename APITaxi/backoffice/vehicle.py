# -*- coding: utf-8 -*-
from flask.ext.security import login_required, current_user, roles_accepted
from flask import request, Blueprint
from ..models import vehicle as vehicle_models, taxis as taxis_models
from .. import db
from ..api import api
from . import ns_administrative
from flask.ext.restplus import fields, Resource, reqparse, abort
from ..utils.make_model import make_model
from ..utils.refresh_db import cache_refresh
from ..forms.taxis import VehicleForm, VehicleDescriptionForm

mod = Blueprint('vehicle', __name__)

vehicle_model = make_model('taxis', 'Vehicle')
vehicle_expect = make_model('taxis', 'Vehicle', filter_id=True)
@ns_administrative.route('vehicles/', endpoint="vehicle")
class Vehicle(Resource):

    @login_required
    @roles_accepted('admin', 'operateur', 'prefecture')
    @api.marshal_with(vehicle_model)
    @api.expect(vehicle_expect)
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    def post(self):
        json = request.get_json()
        if "data" not in json:
            abort(400, message="data is required")
        if len(json['data']) > 250:
            abort(413, message="You can only post 250 vehicles at a time")
        new_vehicle = []
        for vehicle in json['data']:
            form = VehicleForm.from_json(vehicle)
            v = vehicle_models.Vehicle(form.data['licence_plate'])
            v_description = vehicle_models.VehicleDescription(vehicle_id=v.id,
                    added_by=current_user.id)
            v.descriptions.append(v_description)
            form.populate_obj(v)
            form_description = VehicleDescriptionForm.from_json(vehicle)
            form_description.populate_obj(v_description)
            v_description.status = 'off'
            db.session.add(v)
            taxis_models.refresh_taxi(db.session, vehicle=v.id)
            new_vehicle.append(v)
        db.session.commit()
        return {"data": new_vehicle}, 201
