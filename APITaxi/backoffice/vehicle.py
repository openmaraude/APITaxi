# -*- coding: utf-8 -*-
from flask.ext.security import login_required, current_user, roles_accepted
from flask import request, Blueprint, current_app
from ..models import vehicle as vehicle_models, taxis as taxis_models
from ..api import api
from ..descriptors.vehicle import vehicle_model, vehicle_expect
from . import ns_administrative
from flask.ext.restplus import fields, reqparse, abort
from ..forms.taxis import VehicleForm, VehicleDescriptionForm
from APITaxi_utils.resource_metadata import ResourceMetadata
import datetime
mod = Blueprint('vehicle', __name__)

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
        new_vehicles = []
        for vehicle in json['data']:
            form = VehicleForm.from_json(vehicle)
            v = vehicle_models.Vehicle(form.data['licence_plate'])
            v.last_update_at = datetime.datetime.now()
            form.populate_obj(v)
            current_app.extensions['sqlalchemy'].db.session.add(v)
            current_app.extensions['sqlalchemy'].db.session.commit()
            v_description = vehicle_models.VehicleDescription(vehicle_id=v.id,
                    added_by=current_user.id)
            v.descriptions.append(v_description)
            form_description = VehicleDescriptionForm.from_json(vehicle)
            form_description.populate_obj(v_description)
            v_description.status = 'off'
            current_app.extensions['sqlalchemy'].db.session.add(v_description)
            new_vehicles.append(v)
            if not v.id:
                continue
            for taxi in taxis_models.Taxi.query.filter_by(vehicle_id=v.id).all():
                taxis_models.RawTaxi.flush(taxi.id)
        current_app.extensions['sqlalchemy'].db.session.commit()
        return {"data": new_vehicles}, 201

    @login_required
    @roles_accepted('stats')
    @api.doc(False)
    def get(self):
        return self.metadata()
