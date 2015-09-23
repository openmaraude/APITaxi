# -*- coding: utf-8 -*-
from flask.ext.restplus import apidoc
from flask import Blueprint, make_response, render_template
from json import dumps
from ..utils.api import Api

api_blueprint = Blueprint('api', __name__)
api = Api(api_blueprint, ui=False, catch_all_404s=True, title='API version 1.0')


@api_blueprint.route('/doc/', endpoint='doc')
def swagger_ui():
    return render_template('swagger/index.html')


@api.representation('text/html')
def output_html(data, code=200, headers=None):
    if type(data) is dict:
        data = dumps(data)
    resp = make_response(data, code)
    resp.headers.extend(headers or {})
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp

def init_app(app):
    from . import hail, taxi
    app.register_blueprint(api_blueprint)
    app.register_blueprint(apidoc.apidoc)
