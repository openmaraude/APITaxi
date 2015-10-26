# -*- coding: utf-8 -*-
from flask.ext.security import login_required, current_user, roles_accepted
from flask import request, Blueprint
from ..models import vehicle as vehicle_models, taxis as taxis_models
from ..extensions import db
from ..api import api
from . import ns_administrative
from flask.ext.restplus import fields, reqparse, abort
from ..utils.make_model import make_model
from ..forms.taxis import VehicleForm, VehicleDescriptionForm
from ..utils.cache_refresh import cache_refresh
from ..utils.resource_metadata import ResourceMetadata
mod = Blueprint('vehicle', __name__)

vehicle_model = make_model('taxis', 'Vehicle')
vehicle_expect = make_model('taxis', 'Vehicle', filter_id=True)
@ns_administrative.route('vehicles/', endpoint="vehicle")
class Vehicle(ResourceMetadata):
    model = vehicle_models.Vehicle

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
        edited_vehicles_id = []
        new_vehicles = []
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
            if v.id:
                edited_vehicles_id.append(v.id)
            new_vehicles.append(v)
        if edited_vehicles_id:
            cache_refresh(db.session(), {'func': taxis_models.refresh_taxi,
                'kwargs': {'vehicle': edited_vehicles_id}})
        db.session.commit()
        return {"data": new_vehicles}, 201

    @login_required
    @roles_accepted('stats')
    @api.doc(False)
    def get(self):
        return self.metadata()
