# -*- coding: utf8 -*-
from flask import request, redirect, url_for, abort
from flask.ext.restplus import Resource, reqparse
from flask.ext.security import login_required, roles_required,\
        roles_accepted, current_user
from .. import ns_hail, db
from ..models import Hail as HailModel, Customer as CustomerModel
from datetime import datetime


@login_required
@roles_accepted('moteur', 'operateur')
@ns_hail.route('/<int:hail_id>/', endpoint='hailid')
class HailId(Resource):

    def get(self, hail_id):
        hail = HailModel.query.get_or_404(hail_id)
        return hail.to_dict()

    def put(self, hail_id):
        json = request.get_json()
        if not json or not 'hail' in json:
            abort(400)
        json = request.get_json(silent=True)
        hj = json['hail']
        if any(map(lambda f : f not in hj,
                ['customer_id', 'customer_lon', 'customer_lat',
                    'taxi_id', 'status'])):
            abort(400)
        hail = HailModel.query.get_or_404(hail_id)
        if hj['status'] != hail.status and\
            hj['status'] not in ['received_by_taxi',
                'accepted_by_taxi', 'declined_by_taxi',
                'incident_taxi', 'incident_customer']:
            abort(400)
        #We change the status
        if hasattr(hail, hj['status']):
            getattr(hail, hj['status'])()
        if current_user.has_role('moteur'):
            hail.customer_lon = hj['customer_lon']
            hail.customer_lat = hj['customer_lat']
        db.session.commit()
        return hail.to_dict()


@ns_hail.route('/', endpoint='hail_endpoint')
class Hail(Resource):

    @login_required
    @roles_required('moteur')
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('customer_id', type=int, required=True,
                location='json')
        parser.add_argument('customer_lon', type=float, required=True,
               location='json')
        parser.add_argument('customer_lat', type=float, required=True,
                location='json')
        parser.add_argument('taxi_id', type=str, required=True,
                location='json')
        hj = parser.parse_args()
        #@TODO: checker existence du taxi
        #@TODO: checker la disponibilité du taxi
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


