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
from datetime import datetime
import requests, json
from ..descriptors.hail import hail_model
from ..utils.request_wants_json import json_mimetype_required
from ..utils.cache_refresh import cache_refresh

ns_hail = api.namespace('hails', description="Hail API")


parser_put = reqparse.RequestParser()
parser_put.add_argument('customer_lon', type=float, required=True,
        location='hail')
parser_put.add_argument('customer_lat', type=float, required=True,
        location='hail')
parser_put.add_argument('customer_address', type=unicode, required=True,
        location='hail')
parser_put.add_argument('customer_phone_number', type=unicode, required=True,
        location='hail')
parser_put.add_argument('status', type=str, required=True,
                        choices=['received_by_taxi',
                                 'accepted_by_taxi',
                                 'declined_by_taxi',
                                 'incident_taxi',
                                 'incident_customer'],
                        location='hail')
parser_put.add_argument('taxi_phone_number', type=unicode, required=False,
        location='hail')
parser_put.add_argument('rating_ride_reason', type=unicode, required=False,
        location='hail')
parser_put.add_argument('rating_ride', type=int, required=False,
        location='hail')
parser_put.add_argument('incident_customer_reason', type=unicode, required=False,
        location='hail')
parser_put.add_argument('incident_taxi_reason', type=unicode, required=False,
        location='hail')
parser_put.add_argument('reporting_customer', type=bool, required=False,
        location='hail')
parser_put.add_argument('reporting_customer_reason', type=unicode, required=False,
        location='hail')
argument_names = [f.name for f in parser_put.args]
dict_hail =  dict(filter(lambda f: f[0] in argument_names, HailModel.marshall_obj().items()))
dict_hail['operateur'] = fields.String(attribute='operateur.email')
hail_expect_put_details = api.model('hail_expect_put_details', dict_hail)
hail_expect_put = api.model('hail_expect_put',
        {'data': fields.List(fields.Nested(hail_expect_put_details))})
@ns_hail.route('/<int:hail_id>/', endpoint='hailid')
class HailId(Resource):

    @classmethod
    def filter_access(cls, hail):
        if not current_user.id in (hail.operateur_id, hail.added_by) and\
                not current_user.has_role('admin'):
            abort(403, message="You don't have the authorization to view this hail")


    @login_required
    @roles_accepted('admin', 'moteur', 'operateur')
    @api.marshal_with(hail_model)
    @json_mimetype_required
    def get(self, hail_id):
        hail = HailModel.get(hail_id)
        if not hail:
            abort(404, message="Unable to find hail: {}".format(hail_id))
        self.filter_access(hail)
        return {"data": [hail]}

    @login_required
    @roles_accepted('admin', 'moteur', 'operateur')
    @api.marshal_with(hail_model)
    @api.expect(hail_expect_put)
    @json_mimetype_required
    def put(self, hail_id):
        hail = HailModel.query.get_or_404(hail_id)
        self.filter_access(hail)
        if hail.status.startswith("timeout"):
            return {"data": [hail]}
        root_parser = reqparse.RequestParser()
        root_parser.add_argument('data', type=list, location='json')
        req = root_parser.parse_args()
        to_parse = req['data'][0]
        hj = {}
        for arg in parser_put.args:
            if arg.required and arg.name not in to_parse.keys():
                abort(400, message="Field {} is needed".format(arg.name))
            elif arg.name in to_parse.keys():
                try:
                    hj[arg.name] = arg.convert(to_parse[arg.name], '=')
                except ValueError, e:
                    abort(400, message=e.args[0])
        #We change the status
        if hj['status'] == 'accepted_by_taxi':
            if g.version == 1:
                hail.taxi_phone_number = ''
            elif g.version == 2:
                if not 'taxi_phone_number' in hj or hj['taxi_phone_number'] == '':
                    abort(400, message='Taxi phone number is needed')
                else:
                    hail.taxi_phone_number = hj['taxi_phone_number']
        try:
            hail.status = hj['status']
        except AssertionError:
            abort(400, message='Invalid status')
        except ValueError, e:
            abort(400, message=e.args[0])
        except RuntimeError, e:
            abort(403, message=e.args[0])
        if current_user.has_role('moteur'):
            hail.customer_lon = hj['customer_lon']
            hail.customer_lat = hj['customer_lat']
            hail.customer_address = hj['customer_address']
            hail.customer_phone_number = hj['customer_phone_number']
        for ev in ['rating_ride', 'rating_ride_reason',
                'incident_customer_reason', 'incident_taxi_reason',
                'reporting_customer', 'reporting_customer_reason']:
            value = hj.get(ev, None)
            if value is not None:
                try:
                    setattr(hail, ev, value)
                except AssertionError, e:
                    abort(400, message=e.args[0])
                except RuntimeError, e:
                    abort(403)
                except ValueError, e:
                    abort(400, e.args[0])
        cache_refresh(db.session(),
                {'func': HailModel.get.refresh, 'args': [HailModel, hail_id]})
        db.session.commit()
        return {"data": [hail]}


parser_post = reqparse.RequestParser()
parser_post.add_argument('customer_id', type=unicode, required=True)
parser_post.add_argument('customer_lon', type=float, required=True)
parser_post.add_argument('customer_lat', type=float, required=True)
parser_post.add_argument('customer_address', type=unicode, required=True)
parser_post.add_argument('customer_phone_number', type=unicode, required=True)
parser_post.add_argument('taxi_id', type=unicode, required=True)
parser_post.add_argument('operateur', type=unicode, required=True)
argument_names = map(lambda f: f.name, parser_post.args)
dict_hail =  dict(filter(lambda f: f[0] in argument_names, HailModel.marshall_obj().items()))
dict_hail['operateur'] = fields.String(attribute='operateur.email')
hail_expect_post_details = api.model('hail_expect_post_details', dict_hail)
hail_expect = api.model('hail_expect_post',
        {'data': fields.List(fields.Nested(hail_expect_post_details))})

@ns_hail.route('/', endpoint='hail_endpoint')
class Hail(Resource):

    @login_required
    @roles_accepted('admin', 'moteur')
    @api.marshal_with(hail_model)
    @api.expect(hail_expect)
    @json_mimetype_required
    def post(self):
        root_parser = reqparse.RequestParser()
        root_parser.add_argument('data', type=list, location='json')
        req = root_parser.parse_args()
        if 'data' not in req or not isinstance(req['data'], list) or\
                len(req['data']) == 0:
            abort(400, message="data is required")
        if len(req['data']) != 1:
            abort(413, message="You can only post one hail at a time")
        to_parse = req['data'][0]
        hj = {}
        for arg in parser_post.args:
            if arg.name not in to_parse.keys():
                abort(400, message="{} is required".format(arg.name))
            hj[arg.name] = arg.convert(to_parse[arg.name], '=')

        taxi = TaxiModel.query.get(hj['taxi_id'])
        if not taxi:
            return abort(404, message="Unable to find taxi")
        operateur = security_models.User.query.filter_by(email=hj['operateur'])\
                .first()
        if not operateur:
            abort(404, message='Unable to find the taxi\'s operateur')
        desc = taxi.vehicle.get_description(operateur)
        if not desc:
            abort(404, message='Unable to find taxi\'s description')
        if not taxi.is_free() or\
                not taxi.is_fresh(hj['operateur']):
            abort(403, message="The taxi is not available")
        db.session.commit()
        #@TODO: checker que le status est emitted???
        customer = CustomerModel.query.filter_by(id=hj['customer_id'],
                operateur_id=current_user.id).first()
        if not customer:
            customer = CustomerModel()
            customer.id = hj['customer_id']
            customer.operateur_id = current_user.id
            customer.nb_sanctions = 0
            customer.added_via = 'api'
            db.session.add(customer)
        hail = HailModel()
        hail.creation_datetime = datetime.now().isoformat()
        hail.customer_id = hj['customer_id']
        hail.customer_lon = hj['customer_lon']
        hail.customer_lat = hj['customer_lat']
        hail.customer_address = hj['customer_address']
        hail.customer_phone_number = hj['customer_phone_number']
        hail.operateur_id = operateur.id
        hail.added_via = 'api'
        hail.taxi_id = hj['taxi_id']
        db.session.add(hail)
        db.session.commit()
        hail.status = 'emitted'
        hail.status = 'received'
        hail.status = 'sent_to_operator'
        db.session.commit()
        r = None
        try:
            r = requests.post(operateur.hail_endpoint,
                    data=json.dumps(marshal({"data": [hail]}, hail_model)),
                headers={'Content-Type': 'application/json'})
        except requests.exceptions.MissingSchema:
            pass
        if r and 200 <= r.status_code < 300:
            hail.status = 'received_by_operator'
        else:
            current_app.logger.info("Unable to reach hail's endpoint {} of operator {}".format(
                operateur.hail_endpoint, operateur.email))
            hail.status  = 'failure'
        db.session.commit()
        return {"data": [hail]}, 201

