# -*- coding: utf-8 -*-
from . import api
from flask_restplus import Resource, reqparse, fields, abort, marshal
from flask_security import login_required, current_user, roles_accepted
from APITaxi_models.hail import Customer as CustomerModel
from APITaxi_models import db
from flask import request
from ..descriptors.customer import customer_model

@api.route('/customers/<string:customer_id>/')
class Customers(Resource):

    @login_required
    @roles_accepted('admin', 'moteur')
    @api.marshal_with(customer_model)
    def put(self, customer_id):
        moteur_id = None
        if current_user.has_role('admin'):
            parser = reqparse.RequestParser()
            parser.add_argument('moteur_id', location='values')
            moteur_id = parser.parse_args().get('moteur_id', None)
            if not moteur_id and not current_user.has_role('moteur'):
                abort(400, message='You need moteur_id argument')
        if not moteur_id:
            moteur_id = current_user.id

        customer = CustomerModel.query.filter_by(id=customer_id,
                moteur_id=current_user.id).first()
        if not customer:
            abort(404, message="Unable to find customer: {}".format(customer_id))

        json = request.json
        if not 'data' in json:
            abort(400, message="data is needed in json")
        if len(json['data']) == 0:
            return {"data": [customer]}
        if len(json['data']) > 1:
            abort(400, message="length of data must be one")
        customer_json = json['data'][0]
        for arg in ['reprieve_begin', 'reprieve_end', 'ban_begin', 'ban_end']:
            if not arg in customer_json:
                continue
            value = json.get(arg, None)
            setattr(customer, arg, value)
        db.session.add(customer)
        db.session.commit()
        return {"data":[customer]}
