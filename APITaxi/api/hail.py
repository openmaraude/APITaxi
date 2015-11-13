# -*- coding: utf-8 -*-
from flask import request, redirect, url_for, current_app, g
from flask.ext.restplus import Resource, reqparse, fields, abort, marshal
from flask.ext.security import (login_required, roles_required,
        roles_accepted, current_user)
from ..extensions import db, redis_store
from ..api import api
from ..models.hail import Hail as HailModel, Customer as CustomerModel
from ..models.taxis import  Taxi as TaxiModel
from ..models import security as security_models
import requests, json
from ..descriptors.hail import (hail_model, hail_expect_post, hail_expect_put,
        puttable_arguments)
from ..utils.request_wants_json import json_mimetype_required
from ..utils import fields as customFields
from ..utils.validate_json import ValidatorMixin
from geopy.distance import vincenty
from ..tasks import send_request_operator

ns_hail = api.namespace('hails', description="Hail API")
@ns_hail.route('/<string:hail_id>/', endpoint='hailid')
class HailId(Resource, ValidatorMixin):

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
    @api.expect(hail_expect_put)
    @json_mimetype_required
    def put(self, hail_id):
        hail = HailModel.get_or_404(hail_id)
        self.filter_access(hail)
        if hail.status.startswith("timeout"):
            return {"data": [hail]}
        hj = request.json
        self.validate(hj)
        hj = hj['data'][0]

        #We change the status
        if 'status' in hj and  hj['status'] == 'accepted_by_taxi':
            if g.version == 2:
                if not 'taxi_phone_number' in hj or hj['taxi_phone_number'] == '':
                    abort(400, message='Taxi phone number is needed')
                else:
                    hail.taxi_phone_number = hj['taxi_phone_number']
        for ev in puttable_arguments:
            value = hj.get(ev, None)
            if value is None:
                continue
            try:
                setattr(hail, ev, value)
            except AssertionError, e:
                abort(400, message=e.args[0])
            except RuntimeError, e:
                abort(403)
            except ValueError, e:
                abort(400, message=e.args[0])
        db.session.commit()
        return {"data": [hail]}


@ns_hail.route('/', endpoint='hail_endpoint')
class Hail(Resource, ValidatorMixin):

    @login_required
    @roles_accepted('admin', 'moteur')
    @api.marshal_with(hail_model)
    @api.expect(hail_expect_post)
    @json_mimetype_required
    def post(self):
        hj = request.json
        self.validate(hj)
        hj = hj['data'][0]

        taxi = TaxiModel.get_or_404(hj['taxi_id'])
        operateur = security_models.User.filter_by_or_404(
                email=hj['operateur'], message='Unable to find the taxi\'s operateur')
        desc = taxi.vehicle.get_description(operateur)
        if not desc:
            abort(404, message='Unable to find taxi\'s description')
        if not taxi.is_free() or not taxi.is_fresh(hj['operateur']):
            abort(403, message="The taxi is not available")
        customer = CustomerModel.query.filter_by(id=hj['customer_id'],
                operateur_id=current_user.id).first()
        if not customer:
            customer = CustomerModel(hj['customer_id'])
            db.session.add(customer)
        hail = HailModel()
        hail.customer_id = hj['customer_id']
        hail.customer_lon = hj['customer_lon']
        hail.customer_lat = hj['customer_lat']
        hail.customer_address = hj['customer_address']
        hail.customer_phone_number = hj['customer_phone_number']
        hail.taxi_id = hj['taxi_id']
        hail.operateur_id = operateur.id
        hail.status = 'received'

        send_request_operator.apply_async(args=[hail.id, operateur,
            current_app.config['ENV']],
            queue='deployment_'+current_app.config['NOW'])
        current_app.logger.info('queue_name: {}'.format('deployment_'+current_app.config['NOW']))
        db.session.add(hail)
        db.session.commit()

        return {"data": [hail]}, 201
