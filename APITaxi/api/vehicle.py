# -*- coding: utf-8 -*-
from flask_security import login_required, current_user, roles_accepted
from flask import request, Blueprint, current_app
import APITaxi_models as models
from . import api, ns_administrative
from ..descriptors.vehicle import vehicle_model, vehicle_expect
from flask_restplus import fields, reqparse, abort
from APITaxi_utils.resource_metadata import ResourceMetadata
from APITaxi_utils.populate_obj import create_obj_from_json
from APITaxi_utils import reqparse
import datetime
mod = Blueprint('vehicle', __name__)

@ns_administrative.route('vehicles/', endpoint="vehicle")
class Vehicle(ResourceMetadata):
    model = models.Vehicle

    @login_required
    @roles_accepted('admin', 'operateur', 'prefecture')
    @api.marshal_with(vehicle_model)
    @api.expect(vehicle_expect)
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    def post(self):
        parser = reqparse.DataJSONParser(max_length=250)
        new_vehicles = []
        db = current_app.extensions['sqlalchemy'].db
        for vehicle in parser.get_data():
            if 'id' in vehicle.keys():
                del vehicle['id']
            v = models.Vehicle(vehicle['licence_plate'])
            v.last_update_at = datetime.datetime.now()
            create_obj_from_json(models.Vehicle, vehicle, v)
            db.session.add(v)
            db.session.commit()
            v_description = models.VehicleDescription(vehicle_id=v.id,
                    added_by=current_user.id)
            constructor = models.Constructor(vehicle['constructor'])
            model = models.Model(vehicle['model'])
            db.session.add(model)
            db.session.add(constructor)
            db.session.commit()
            v_description.constructor = constructor
            v_description.model = model
            v.descriptions.append(v_description)
            create_obj_from_json(models.VehicleDescription,
                    vehicle, v_description)
            v_description.status = 'off'
            db.session.add(v_description)
            new_vehicles.append(v)
            if not v.id:
                continue
            for taxi in models.Taxi.query.filter_by(vehicle_id=v.id).all():
                models.RawTaxi.flush(taxi.id)
        db.session.commit()
        return {"data": new_vehicles}, 201

    @login_required
    @roles_accepted('stats')
    @api.doc(False)
    def get(self):
        return self.metadata()
