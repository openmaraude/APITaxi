# -*- coding: utf-8 -*-
from flask_security import login_required, roles_accepted
from . import api, ns_administrative
from ..descriptors.vehicle import vehicle_model, vehicle_expect
import APITaxi_models as models
from APITaxi_utils import reqparse, resource_metadata

@ns_administrative.route('vehicles/', endpoint="vehicle")
class Vehicle(resource_metadata.ResourceMetadata):
    model = models.Vehicle

    @login_required
    @roles_accepted('admin', 'operateur', 'prefecture')
    @api.marshal_with(vehicle_model)
    @api.expect(vehicle_expect, validate=True)
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    def post(self):
        parser = reqparse.DataJSONParser(max_length=250, filter_=vehicle_expect)
        return {"data": [models.Vehicle(**v) for v in parser.get_data()]}, 201

    @login_required
    @roles_accepted('stats')
    @api.doc(False)
    def get(self):
        return self.metadata()
