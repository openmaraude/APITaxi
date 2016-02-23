# -*- coding: utf-8 -*-
from flask.ext.restplus import apidoc, Api
from flask import Blueprint, render_template

api_blueprint = Blueprint('api', __name__)
api = Api(api_blueprint, doc=False, catch_all_404s=True, title='API version 2.0')

ns_administrative = api.namespace('administrative',
        description="Administrative APIs", path='/')

@api_blueprint.route('/doc/', endpoint='doc')
def swagger_ui():
    return render_template('swagger/index.html')

def init_app(app):
    from . import hail, taxi, ads, drivers, zupc, profile, vehicle
    app.register_blueprint(api_blueprint)
    app.register_blueprint(apidoc.apidoc)
