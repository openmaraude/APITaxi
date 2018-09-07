# -*- coding: utf-8 -*-
from APITaxi_utils import resource_metadata, resource_file_or_json, reqparse
import APITaxi_models as models
from flask_security import login_required, roles_accepted, current_user
from . import api, ns_administrative, extensions
from ..descriptors.ads import ads_expect, ads_post
from flask_restplus import marshal

@ns_administrative.route("/ads/", endpoint="ads")
class ADS(resource_metadata.ResourceMetadata, resource_file_or_json.ResourceFileOrJSON):
    model = models.ADS
    filetype = "ADS"
    documents = extensions.documents

    @login_required
    @roles_accepted("admin", "operateur", "prefecture")
    @api.doc(responses={404:"Resource not found",
                        403:"You're not authorized to view it"})
    @api.expect(ads_expect, validate=True)
    @api.response(200, "Success", ads_post)
    def post(self):
        return super(ADS, self).post()

    def post_json(self):
        parser = reqparse.DataJSONParser(max_length=250, filter_=ads_expect)
        return marshal({"data": [models.ADS(**a) for a in parser.get_data() or []]}, ads_post), 201
