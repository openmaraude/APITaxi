# -*- coding: utf-8 -*-
from . import ns_administrative
from flask_security import login_required, roles_accepted
from APITaxi_utils import reqparse, resource_file_or_json, resource_metadata
import APITaxi_models as models
from . import api
from ..descriptors.drivers import driver_fields, driver_details_expect
from flask_restx import marshal
from .extensions import documents

@ns_administrative.route('/drivers/')
class Drivers(resource_metadata.ResourceMetadata, resource_file_or_json.ResourceFileOrJSON):
    model = models.Driver
    filetype = 'conducteur'
    documents = documents

    @login_required
    @roles_accepted('admin', 'operateur', 'prefecture')
    @api.expect(driver_details_expect, validate=True)
    @api.response(200, 'Success', driver_fields)
    def post(self):
        return super(Drivers, self).post()


    def post_json(self):
        parser = reqparse.DataJSONParser(max_length=250, filter_=driver_details_expect)
        return marshal({'data': [models.Driver(**d) for d in parser.get_data()]}, driver_fields), 201
