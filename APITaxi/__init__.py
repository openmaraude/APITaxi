# -*- coding: utf8 -*-
VERSION = (0, 1, 0)
__author__ = 'Vincent Lara'
__contact__ = "vincent.lara@data.gouv.fr"
__homepage__ = "https://github.com/"
__version__ = ".".join(map(str, VERSION))


from flask import Flask, request_started, request, abort, request_finished
from flask.ext.security import Security, SQLAlchemyUserDatastore
from flask.ext.script import Manager
from flask_bootstrap import Bootstrap
import os
from models import db, security as security_models
from flask.ext.redis import FlaskRedis
from flask.ext.restplus import abort
from .utils.redis_geo import GeoRedis

redis_store = FlaskRedis.from_custom_provider(GeoRedis)
user_datastore = SQLAlchemyUserDatastore(db, security_models.User,
                            security_models.Role)

def check_version(sender, **extra):
    if len(request.accept_mimetypes) == 0 or\
        request.accept_mimetypes[0][0] != 'application/json':
        return
    version = request.headers.get('X-VERSION', None)
    if version != '1':
        abort(404)


def add_version_header(sender, response, **extra):
    response.headers['X-VERSION'] = request.headers.get('X-VERSION')


def create_app():
    app = Flask(__name__)
    app.config.from_object('default_settings')
    if 'APITAXI_CONFIG_FILE' in os.environ:
        app.config.from_envvar('APITAXI_CONFIG_FILE')

    db.init_app(app)
    security = Security(app, user_datastore)
    redis_store.init_app(app)
    import backoffice
    backoffice.init_app(app)
    from . import api
    api.init_app(app)
    Bootstrap(app)

    manager = Manager(app)
    request_started.connect(check_version, app)
    request_finished.connect(add_version_header, app)
    return app
