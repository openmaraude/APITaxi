# -*- coding: utf8 -*-
from flask import request, redirect, url_for, abort
from flask.ext.restplus import Resource
from flask.ext.security import login_required, roles_required,\
        roles_accepted, current_user
from .. import ns_hail, db
from ..models import Hail as HailModel
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
                ['client_id', 'client_lon', 'client_lat',
                    'taxi_id', 'status'])):
            abort(400)
        hail = HailModel.query.get_or_404(hail_id)
        if hj['status'] != hail.status and\
            hj['status'] not in ['received_by_taxi',
                'accepted_by_taxi', 'declined_by_taxi',
                'incident_taxi', 'incident_client']:
            abort(400)
        #We change the status
        if hasattr(hail, hj['status']):
            getattr(hail, hj['status'])()
        if current_user.has_role('moteur'):
            hail.client_lon = hj['client_lon']
            hail.client_lat = hj['client_lat']
        db.session.commit()
        return hail.to_dict()


@login_required
@roles_required('moteur')
@ns_hail.route('/', endpoint='hail_endpoint')
class Hail(Resource):
    def post(self):
        json = request.get_json()
        if not json:
            abort(400)
        if any(map(lambda f : f not in json['hail'],
                ['client_id', 'client_lon', 'client_lat',
                    'taxi_id'])):
            abort(400)
        #@TODO: faire validation des arguments avec http://flask-restful.readthedocs.org/en/0.3.2/reqparse.html
        #@TODO: checker existence du taxi
        #@TODO: checker la disponibilité du taxi
        #@TODO: créer profil client s'il n'existe pas
        #@TODO: checker que le status est emitted???
        hj = json['hail']
        hail = HailModel()
        hail.creation_datetime = datetime.now().isoformat()
        hail.client_id = hj['client_id']
        hail.client_lon = hj['client_lon']
        hail.client_lat = hj['client_lat']
        hail.taxi_id = hj['taxi_id']
        hail.received()
        db.session.add(hail)
        db.session.commit()
        return redirect(url_for('hailid', hail_id=hail.id))


