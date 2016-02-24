# -*- coding: utf-8 -*-
from flask.ext.security import login_required, current_user, roles_accepted
from flask import request, Blueprint, current_app
from APITaxi_models import vehicle as vehicle_models, taxis as taxis_models
from . import api, ns_administrative
from ..descriptors.vehicle import vehicle_model, vehicle_expect
from flask.ext.restplus import fields, reqparse, abort
from APITaxi_utils.resource_metadata import ResourceMetadata
from APITaxi_utils.populate_obj import create_obj_from_json
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
        db = current_app.extensions['sqlalchemy'].db
        for vehicle in json['data']:
            v = vehicle_models.Vehicle(vehicle['licence_plate'])
            v.last_update_at = datetime.datetime.now()
            create_obj_from_json(vehicle_models.Vehicle, vehicle, v)
            db.session.add(v)
            db.session.commit()
            v_description = vehicle_models.VehicleDescription(vehicle_id=v.id,
                    added_by=current_user.id)
            constructor = vehicle_models.Constructor(vehicle['constructor'])
            model = vehicle_models.Model(vehicle['model'])
            db.session.add(model)
            db.session.add(constructor)
            db.session.commit()
            v_description.constructor = constructor
            v_description.model = model
            v.descriptions.append(v_description)
            create_obj_from_json(vehicle_models.VehicleDescription,
                    vehicle, v_description)
            v_description.status = 'off'
            db.session.add(v_description)
            new_vehicles.append(v)
            if not v.id:
                continue
            for taxi in taxis_models.Taxi.query.filter_by(vehicle_id=v.id).all():
                taxis_models.RawTaxi.flush(taxi.id)
        db.session.commit()
        return {"data": new_vehicles}, 201

    @login_required
    @roles_accepted('stats')
    @api.doc(False)
    def get(self):
        return self.metadata()
