# -*- coding: utf-8 -*-
from flask import request, redirect, url_for
from flask.ext.restplus import Resource, reqparse, fields, abort, marshal
from flask.ext.security import login_required, roles_required,\
        roles_accepted, current_user
from .. import db, redis_store, user_datastore
from ..api import api
from ..models import (Hail as HailModel, Customer as CustomerModel,
    Taxi as TaxiModel, security as security_models)
from datetime import datetime
from ..utils.make_model import make_model
import requests, json

ns_hail = api.namespace('hails', description="Hail API")

hail_model = make_model('hail', 'Hail')

parser_put = reqparse.RequestParser()
parser_put.add_argument('customer_lon', type=float, required=True,
        location='hail')
parser_put.add_argument('customer_lat', type=float, required=True,
        location='hail')
parser_put.add_argument('status', type=str, required=True,
                        choices=['received_by_taxi',
                                 'accepted_by_taxi',
                                 'declined_by_taxi',
                                 'incident_taxi',
                                 'incident_customer'],
                        location='hail')
argument_names = map(lambda f: f.name, parser_put.args)
hail_expect_put_details = api.model('hail_expect_put_details',
                                dict(filter(lambda f: f[0] in argument_names, HailModel.marshall_obj().items())))
hail_expect_put = api.model('hail_expect_put', {'data': fields.List(fields.Nested(hail_expect_put_details))})

@login_required
@roles_accepted('moteur', 'operateur')
@ns_hail.route('/<int:hail_id>/', endpoint='hailid')
class HailId(Resource):

    @api.marshal_with(hail_model)
    def get(self, hail_id):
        hail = HailModel.query.get_or_404(hail_id)
        return {"data": [hail]}

    @api.marshal_with(hail_model)
    @api.expect(hail_expect_put)
    def put(self, hail_id):
        root_parser = reqparse.RequestParser()
        root_parser.add_argument('data', type=list, location='json')
        req = root_parser.parse_args()
        to_parse = req['data'][0]
        hj = {}
        for arg in parser_put.args:
            if arg.name not in to_parse.keys():
                abort(400)
            hj[arg.name] = arg.convert(to_parse[arg.name], '=')
        hail = HailModel.query.get_or_404(hail_id)
        #We change the status
        if hasattr(hail, hj['status']):
            getattr(hail, hj['status'])()
        if current_user.has_role('moteur'):
            hail.customer_lon = hj['customer_lon']
            hail.customer_lat = hj['customer_lat']
            db.session.commit()
        return {"data": [hail]}


parser_post = reqparse.RequestParser()
parser_post.add_argument('customer_id', type=str,
                         required=True)
parser_post.add_argument('customer_lon', type=float,
                         required=True)
parser_post.add_argument('customer_lat', type=float,
                         required=True)
parser_post.add_argument('taxi_id', type=str,
                         required=True)
argument_names = map(lambda f: f.name, parser_post.args)
hail_expect_post_details = api.model('hail_expect_post_details',
                                dict(filter(lambda f: f[0] in argument_names, HailModel.marshall_obj().items())))
hail_expect = api.model('hail_expect_post', {'data': fields.List(fields.Nested(hail_expect_post_details))})

@ns_hail.route('/', endpoint='hail_endpoint')
class Hail(Resource):

    @login_required
    @roles_required('moteur')
    @api.marshal_with(hail_model)
    @api.expect(hail_expect)
    def post(self):
        root_parser = reqparse.RequestParser()
        root_parser.add_argument('data', type=list, location='json')
        req = root_parser.parse_args()
        if 'data' not in req or not isinstance(req['data'], list) or len(req['data']) == 0:
            abort(400)
        if len(req['data']) != 1:
            abort(413)
        to_parse = req['data'][0]
        hj = {}
        for arg in parser_post.args:
            if arg.name not in to_parse.keys():
                abort(400)
            hj[arg.name] = arg.convert(to_parse[arg.name], '=')

        taxi = TaxiModel.query.get(hj['taxi_id'])
        if not taxi:
            return abort(404, message="Unable to find taxi")
        if taxi.status != 'free':
            return abort(403, message="The taxi is not available")
        taxi.status = 'answering'
        db.session.commit()
        operator, _ = taxi.get_operator(redis_store, user_datastore)
        if not operator:
            abort(404, message='Unable to find the taxi\'s operator')
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
        hail.operateur_id = operator.id
        hail.added_via = 'api'
        hail.taxi_id = hj['taxi_id']
        db.session.add(hail)
        db.session.commit()
        hail.received()
        hail.sent_to_operator()
        db.session.commit()
        r = None
        try:
            r = requests.post(operator.hail_endpoint,
                    data=json.dumps({"data": [marshal(hail, hail_model)]}),
                headers={'Content-Type': 'application/json'})
        except requests.exceptions.MissingSchema:
            abort(503, message="Unable to reach operator")
        if r.status_code == 201:
            hail.received_by_operator()
        else:
            hail.failure()
        db.session.commit()
        return {"data": [hail]}, 201

