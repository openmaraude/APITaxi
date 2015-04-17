# -*- coding: utf8 -*-
from flask_restful import Resource, reqparse
from flask.ext.security import login_required, current_user, roles_accepted
from flask import request, redirect, url_for, abort, jsonify
from ..utils import create_obj_from_json
from ..models import taxis as taxis_models
from .. import db, api


@api.route('/vehicle/', endpoint="vehicle")
class ADS(Resource):

    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @login_required
    @roles_accepted('admin', 'operateur')
    def post(self):
        json = request.get_json()
        if "vehicle" not in json:
            abort(400)
        new_vehicle = None
        try:
            new_vehicle = create_obj_from_json(taxis_models.Vehicle,
                json['vehicle'])
        except KeyError as e:
            print "Error :",e
            abort(400)
        db.session.add(new_vehicle)
        db.session.commit()
        return jsonify(new_vehicle.as_dict())
