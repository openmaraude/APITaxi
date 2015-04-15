# -*- coding: utf8 -*-
from flask import request, redirect, url_for
from flask.ext.restplus import Resource
from flask.ext.security import login_required, roles_required,\
        roles_accepted, current_user
from .. import ns, db
from ..models import Hail as HailModel
from datetime import datetime

@ns.route('/<string:hail_id>/', endpoint='hailid')
@login_required
@roles_accepted('moteur', 'operateur')
class HailId(Resource):

    def get(self, hail_id):
        hail = HailModel.query.first_or_404(hail_id)
        return hail.to_dict()

    def put(self, hail_id):
        if not json:
            abort(400)
        if any(lambda f : f not in json['hail'],
                ['client_id', 'client_lon', 'client_lat',
                    'taxi_id', 'status']):
            abort(400)
        hj = json['hail']
        hail = HailModel.get_or_404(hail_id)
        json = request.get_json(silent=True)
        if hj['status'] not in ['received_by_taxi',
                'accepted_by_taxi', 'declined_by_taxi',
                'incident_taxi', 'incident_client']:
            abort(400)
        #We change the status
        getattr(hail, hj['status'])()
        db.session.commit()
        return hail.as_dict()


@ns.route('/', endpoint='hail_endpoint')
#@login_required
#@roles_required('moteur')
class Hail(Resource):
    def post(self):
        json = get_json()
        if not json:
            abort(400)
        if any(lambda f : f not in json['hail'],
                ['client_id', 'client_lon', 'client_lat',
                    'taxi_id']):
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


