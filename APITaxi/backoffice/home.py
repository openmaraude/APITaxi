# -*- coding: utf8 -*-
from flask import Blueprint, render_template, url_for, jsonify
from flask.ext.security import login_required, current_user
from ..utils import request_wants_json

mod = Blueprint('home_bo', __name__)

@mod.route('/')
@login_required
def home():
    if not request_wants_json():
        return render_template('base.html')
    links = {}
    if current_user.has_role('operateur') or current_user.has_role('admin'):
        links.update(
                {'vehicle': {
                    'href': url_for('api.vehicle', _external=True),
                    'methods': set(['POST', 'PUT'])},
                 'driver': {
                    'href': url_for('api.drivers', _external=True),
                    'methods': set(['POST', 'PUT'])},
                 'ads': {
                    'href': url_for('api.ads', _external=True),
                    'methods': set(['POST', 'PUT'])},
                 'taxi_id': {
                    'href': url_for('api.taxi_id', _external=True, taxi_id="_id_"),
                    'methods': set(['PUT', 'GET'])},
                 'hail': {
                     'href': url_for('api.hail_endpoint', _external=True),
                     'methods': set(['PUT', 'GET'])
                     }
                }
         )
    if current_user.has_role('moteur') or current_user.has_role('admin'):
        links.update(
                {
                'taxi_id': {
                    'href': url_for('api.taxi_id', _external=True, taxi_id="_id_"),
                    'methods': links.get('taxi_id', {'methods': set()})['methods']\
                                        .union(set(['GET']))
                }
                })
        links.update(
                {
                'hail': {
                    'href': url_for('api.hail_endpoint'),
                    'methods': links.get('hail', {'methods': set()})['methods']\
                                        .union(set(['POST', 'PUT', 'GET']))
                }
                })
    for k, v in links.items():
        links[k]['methods'] = list(v['methods'])

    return jsonify({'links': links})



