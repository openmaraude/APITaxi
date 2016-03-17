# -*- coding: utf-8 -*-
from flask import request, current_app, g
from flask.ext.restplus import Resource, reqparse, fields, abort, marshal
from flask.ext.security import (login_required, roles_required,
        roles_accepted, current_user)
from ..extensions import redis_store
from ..api import api
from APITaxi_models.hail import Hail as HailModel, Customer as CustomerModel
from APITaxi_models.taxis import  RawTaxi, TaxiRedis
from APITaxi_models import security as security_models
from ..descriptors.hail import (hail_model, hail_expect_post, hail_expect_put,
        puttable_arguments)
from APITaxi_utils.request_wants_json import json_mimetype_required
from geopy.distance import vincenty
from ..tasks import send_request_operator
from APITaxi_utils import influx_db
from datetime import datetime

ns_hail = api.namespace('hails', description="Hail API")
@ns_hail.route('/<string:hail_id>/', endpoint='hailid')
class HailId(Resource):

    @classmethod
    def filter_access(cls, hail):
        if not current_user.id in (hail.operateur_id, hail.added_by) and\
                not current_user.has_role('admin'):
            abort(403, message="You don't have the authorization to view this hail")


    @login_required
    @roles_accepted('admin', 'moteur', 'operateur')
    @json_mimetype_required
    def get(self, hail_id):
        hail = HailModel.get_or_404(hail_id)
        self.filter_access(hail)
        return_ = marshal({"data": [hail]},hail_model)
        return_['data'][0]['taxi']['crowfly_distance'] = vincenty(
                (return_['data'][0]['taxi']['position']['lat'],
                return_['data'][0]['taxi']['position']['lon']),
                (return_['data'][0]['customer_lat'],
                 return_['data'][0]['customer_lon'])
                ).kilometers
        return return_

    @login_required
    @roles_accepted('admin', 'moteur', 'operateur')
    @api.marshal_with(hail_model)
    @api.expect(hail_expect_put, validate=True)
    @json_mimetype_required
    def put(self, hail_id):
        hail = HailModel.get_or_404(hail_id)
        self.filter_access(hail)
        if hail.status.startswith("timeout"):
            return {"data": [hail]}
        hj = request.json
        hj = hj['data'][0]

        #We change the status
        if 'status' in hj and  hj['status'] == 'accepted_by_taxi':
            if g.version == 2:
                if not 'taxi_phone_number' in hj or hj['taxi_phone_number'] == '':
                    abort(400, message='Taxi phone number is needed')
                else:
                    hail.taxi_phone_number = hj['taxi_phone_number']
        for ev in puttable_arguments:
            if current_user.id != hail.added_by and ev.startswith('customer'):
                continue
            value = hj.get(ev, None)
            if value is None:
                continue
            try:
                setattr(hail, ev, value)
            except AssertionError, e:
                if e.args:
                    abort(400, message=e.args[0])
                else:
                    abort(400,
                        message="Unable to set {} to {}, validation failed".format(ev, value))
            except RuntimeError, e:
                abort(403)
            except ValueError, e:
                abort(400, message=e.args[0])
        current_app.extensions['sqlalchemy'].db.session.add(hail)
        current_app.extensions['sqlalchemy'].db.session.commit()
        return {"data": [hail]}


@ns_hail.route('/', endpoint='hail_endpoint')
class Hail(Resource):

    @login_required
    @roles_accepted('admin', 'moteur')
    @api.expect(hail_expect_post, validate=True)
    @api.response(201, 'Success', hail_model)
    @json_mimetype_required
    def post(self):
        hj = request.json
        hj = hj['data'][0]

        operateur = security_models.User.filter_by_or_404(
                email=hj['operateur'],
                message='Unable to find the taxi\'s operateur')

        descriptions = RawTaxi.get((hj['taxi_id'],), operateur.id)
        if len(descriptions) == 0 or len(descriptions[0]) == 0:
            abort(404, message='Unable to find taxi {} of {}'.format(
                hj['taxi_id'], hj['operateur']))
        if descriptions[0][0]['vehicle_description_status'] != 'free' or\
                not TaxiRedis(hj['taxi_id']).is_fresh(hj['operateur']):
            abort(403, message="The taxi is not available")
        customer = CustomerModel.query.filter_by(id=hj['customer_id'],
                operateur_id=current_user.id).first()
        if not customer:
            customer = CustomerModel(hj['customer_id'])
            current_app.extensions['sqlalchemy'].db.session.add(customer)
        taxi_score = redis_store.zscore(current_app.config['REDIS_GEOINDEX'],
                '{}:{}'.format(hj['taxi_id'], operateur.email))
        r = redis_store.geodecode(int(taxi_score)) if taxi_score else None
        taxi_pos = r[0] if r else None

        hail = HailModel()
        hail.customer_id = hj['customer_id']
        hail.customer_lon = hj['customer_lon']
        hail.customer_lat = hj['customer_lat']
        hail.customer_address = hj['customer_address']
        hail.customer_phone_number = hj['customer_phone_number']
        hail.taxi_id = hj['taxi_id']
        hail.initial_taxi_lat = taxi_pos[0] if r else None
        hail.initial_taxi_lon = taxi_pos[1] if r else None
        hail.operateur_id = operateur.id
        hail.status = 'received'
        current_app.extensions['sqlalchemy'].db.session.add(hail)
        current_app.extensions['sqlalchemy'].db.session.commit()

        send_request_operator.apply_async(args=[hail.id,
            operateur.hail_endpoint(current_app.config['ENV']),
            unicode(operateur.operator_header_name),
            unicode(operateur.operator_api_key), operateur.email],
            queue='send_hail_'+current_app.config['NOW'])

        client = influx_db.get_client(current_app.config['INFLUXDB_TAXIS_DB'])
        try:
            client.write_points([{
                "measurement": "hails_created",
                "tags": {
                    "added_by": current_user.email,
                    "operator": operateur.email,
                    "zupc": descriptions[0][0]['ads_zupc_id'],
                    },
                "time": datetime.utcnow().strftime('%Y%m%dT%H:%M:%SZ'),
                "fields": {
                    "value": 1
                }
                }])
        except Exception as e:
            current_app.logger.error('Influxdb Error: {}'.format(e))
        result = marshal({"data": [hail]}, hail_model)
        result['data'][0]['taxi']['lon'] = hail.initial_taxi_lon
        result['data'][0]['taxi']['lat'] = hail.initial_taxi_lat
        return result, 201
