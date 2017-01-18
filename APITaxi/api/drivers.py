# -*- coding: utf-8 -*-
from . import ns_administrative
from flask_security import login_required, roles_accepted
from APITaxi_utils.resource_metadata import ResourceMetadata
from APITaxi_utils.populate_obj import create_obj_from_json
from APITaxi_utils.resource_file_or_json import ResourceFileOrJSON
from APITaxi_utils import reqparse
import APITaxi_models as models
from . import api
from ..descriptors.drivers import driver_fields, driver_details_expect
from flask_restplus import marshal, abort
from .extensions import documents

@ns_administrative.route('drivers/')
class Drivers(ResourceMetadata, ResourceFileOrJSON):
    model = models.Driver
    filetype = 'conducteur'
    documents = documents

    @login_required
    @roles_accepted('admin', 'operateur', 'prefecture')
    @api.expect(driver_details_expect)
    @api.response(200, 'Success', driver_fields)
    def post(self):
        return super(Drivers, self).post()


    def post_json(self):
        parser = reqparse.DataJSONParser(max_length=250)
        new_drivers = []
        for driver in parser.get_data():
            departement = None
            if 'numero' in driver['departement']:
                departement = models.Departement.\
                    filter_by_or_404(numero=driver['departement']['numero'])
            elif 'nom' in driver['departement']:
                departement = models.Departement.\
                    filter_by_or_404(nom=driver['departement']['nom'])
            driver_obj = create_obj_from_json(models.Driver, driver)
            driver_obj.departement_id = departement.id
            models.db.session.add(driver_obj)
            new_drivers.append(driver_obj)
        models.db.session.commit()
        for driver in new_drivers:
            cur = models.db.session.connection().connection.cursor()
            cur.execute("""
                UPDATE taxi set driver_id = %s WHERE driver_id IN (
                    SELECT id FROM driver WHERE professional_licence = %s
                    AND departement_id = %s
                )""",
                (driver.id, driver.professional_licence, driver.departement_id)
            )
        models.db.session.commit()
        return marshal({'data': new_drivers}, driver_fields), 201
