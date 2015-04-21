# -*- coding: utf8 -*-
from flask import request, redirect, url_for, abort
from flask.ext.restplus import Resource, reqparse, fields
from flask.ext.security import login_required, roles_required,\
        roles_accepted, current_user
from .. import ns_hail, db, api
from ..models import Hail as HailModel, Customer as CustomerModel, Taxi as TaxiModel
from datetime import datetime


hail_model_details = api.model('hail_model_details', HailModel.marshall_obj())
hail_model = api.model('hail_model', {"hail": fields.Nested(hail_model_details)})


parser_put = reqparse.RequestParser()
parser_put.add_argument('customer_lon', type=float, required=True,
        location='json')
parser_put.add_argument('customer_lat', type=float, required=True,
        location='json')
parser_put.add_argument('status', type=str, required=True,
                        choices=['received_by_taxi',
                                 'accepted_by_taxi',
                                 'declined_by_taxi',
                                 'incident_taxi',
                                 'incident_customer'],
                        location='json')
argument_names = map(lambda f: f.name, parser_put.args)
hail_expect_put_details = api.model('hail_expect_put_details',
                                dict(filter(lambda f: f[0] in argument_names, HailModel.marshall_obj().items())))
hail_expect_put = api.model('hail_expect_put', {'hail': fields.Nested(hail_expect_put_details)})

@login_required
@roles_accepted('moteur', 'operateur')
@ns_hail.route('/<int:hail_id>/', endpoint='hailid')
class HailId(Resource):

    @api.marshal_with(hail_model)
    def get(self, hail_id):
        hail = HailModel.query.get_or_404(hail_id)
        return hail.to_dict()

    @api.marshal_with(hail_model)
    @api.expect(hail_expect_put)
    def put(self, hail_id):
        root_parser = reqparse.RequestParser()
        root_parser.add_argument('hail', type=dict, location='json')
        hj = parser_post.parse_args(req=root_parser.parse_args())
        hail = HailModel.query.get_or_404(hail_id)
        #We change the status
        if hasattr(hail, hj['status']):
            getattr(hail, hj['status'])()
        if current_user.has_role('moteur'):
            hail.customer_lon = hj['customer_lon']
            hail.customer_lat = hj['customer_lat']
        db.session.commit()
        return hail.to_dict()


parser_post = reqparse.RequestParser()
parser_post.add_argument('customer_id', type=int, required=True,
        location='json')
parser_post.add_argument('customer_lon', type=float, required=True,
        location='json')
parser_post.add_argument('customer_lat', type=float, required=True,
        location='json')
parser_post.add_argument('taxi_id', type=str, required=True,
        location='json')
argument_names = map(lambda f: f.name, parser_post.args)
hail_expect_post_details = api.model('hail_expect_post_details',
                                dict(filter(lambda f: f[0] in argument_names, HailModel.marshall_obj().items())))
hail_expect = api.model('hail_expect_post', {'hail': fields.Nested(hail_expect_post_details)})

@ns_hail.route('/', endpoint='hail_endpoint')
class Hail(Resource):

    @api.marshal_with(hail_model)
    @api.expect(hail_expect)
    @login_required
    @roles_required('moteur')
    def post(self):
        root_parser = reqparse.RequestParser()
        root_parser.add_argument('hail', type=dict, location='json')
        hj = parser_post.parse_args(req=root_parser.parse_args())
        taxi = TaxiModel.query.get(hj['taxi_id'])
        if not taxi:
            return abort(404)
        if taxi.status != 'free':
            return abort(403)
        taxi.status = 'answering'
        db.session.commit()
        #@TODO: checker que le status est emitted???
        customer = CustomerModel.query.filter_by(id=hj['customer_id'],
                operateur_id=current_user.id)
        if not customer:
            customer = CustomerModel()
            customer.id = hj['customer_id']
            customer.operateur_id = current_user.id
            customer.nb_sanctions = 0
            db.session.add(customer)
        hail = HailModel()
        hail.creation_datetime = datetime.now().isoformat()
        hail.customer_id = hj['customer_id']
        hail.customer_lon = hj['customer_lon']
        hail.customer_lat = hj['customer_lat']
        hail.taxi_id = hj['taxi_id']
        db.session.add(hail)
        db.session.commit()
        #send hail to operateur
        hail.received()
        db.session.commit()
        return redirect(url_for('hailid', hail_id=hail.id))


