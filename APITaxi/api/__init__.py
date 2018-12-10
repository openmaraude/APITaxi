# -*- coding: utf-8 -*-
from flask_restplus import apidoc, Api
from flask import Blueprint, render_template
from flask_cors import cross_origin

api_blueprint = Blueprint('api', __name__)
api = Api(api_blueprint, doc=False, catch_all_404s=True,
        title='API version 2.0')

ns_administrative = api.namespace('administrative',
        description="Administrative APIs", path='/')

def init_app(app):
    from . import (hail, taxi, ads, drivers, zupc, profile, vehicle, documents,
                   users, customer, waiting_time)
    api.init_app(app, add_specs=False)
    app.register_blueprint(api_blueprint)
    app.register_blueprint(apidoc.apidoc)

    @app.route('/swagger.json', endpoint='api.specs')
    @cross_origin()
    def swagger():
        return render_template('swagger.json', host=app.config['SERVER_NAME']), 200,
    {'Content-Type': 'application/json'}

    @api.errorhandler(AssertionError)
    @api.errorhandler(KeyError)
    def assertion_error(error):
        if error.args:
            message = error.args[0]
        elif error.message:
            message = error.message
        else:
            message = error.__class__
        return {"message": message}, 400
