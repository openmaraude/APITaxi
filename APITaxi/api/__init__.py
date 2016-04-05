# -*- coding: utf-8 -*-
from flask.ext.restplus import apidoc, Api
from flask import Blueprint, render_template

api_blueprint = Blueprint('api', __name__)
api = Api(api_blueprint, doc=False, catch_all_404s=True,
        title='API version 2.0')

ns_administrative = api.namespace('administrative',
        description="Administrative APIs", path='/')

def init_app(app):
    from . import hail, taxi, ads, drivers, zupc, profile, vehicle, documents
    api.init_app(app, add_specs=False)
    app.register_blueprint(api_blueprint)
    app.register_blueprint(apidoc.apidoc)

    @app.route('/swagger.json', endpoint='api.specs')
    def swagger():
        return render_template('swagger.json', host=app.config['SERVER_NAME']), 200,
    {'Content-Type': 'application/json'}
