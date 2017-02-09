# -*- coding: utf-8 -*-
from APITaxi_utils.resource_metadata import ResourceMetadata
from APITaxi_utils.populate_obj import create_obj_from_json
from APITaxi_utils.reqparse import DataJSONParser
from APITaxi_utils.resource_file_or_json import ResourceFileOrJSON
import APITaxi_models as models
from flask_security import login_required, roles_accepted, current_user
from . import api, ns_administrative, extensions
from ..descriptors.ads import ads_expect, ads_post
from flask_restplus import abort, marshal

@ns_administrative.route("ads/", endpoint="ads")
class ADS(ResourceMetadata, ResourceFileOrJSON):
    model = models.ADS
    filetype = "ADS"
    documents = extensions.documents

    @login_required
    @roles_accepted("admin", "operateur", "prefecture")
    @api.doc(responses={404:"Resource not found",
                        403:"You're not authorized to view it"})
    @api.expect(ads_expect)
    @api.response(200, "Success", ads_post)
    def post(self):
        return super(ADS, self).post()

    def post_json(self):
        data_parser = DataJSONParser(max_length=250)
        new_ads = []
        for ads in data_parser.get_data():
            try:
                ads_db = create_obj_from_json(models.ADS, ads)
            except KeyError as e:
                abort(400, message=e)
            models.db.session.add(ads_db)
            new_ads.append(ads_db)
        models.db.session.commit()
        for ads in new_ads:
            cur = models.db.session.connection().connection.cursor()
            cur.execute(""" UPDATE taxi set ads_id = %s WHERE ads_id IN (
                                SELECT id FROM "ADS"  WHERE numero = %s
                                AND insee = %s)
                        """, (ads.id, ads.numero, ads.insee)
            )
        models.db.session.commit()
        return marshal({"data": new_ads}, ads_post), 201
