# -*- coding: utf-8 -*-
VERSION = (0, 1, 0)
__author__ = 'Vincent Lara'
__contact__ = "vincent.lara@data.gouv.fr"
__homepage__ = "https://github.com/"
__version__ = ".".join(map(str, VERSION))

from flask import Flask, request_started, request, request_finished, g
from flask.ext.security import Security, SQLAlchemyUserDatastore
from flask_bootstrap import Bootstrap
import os
from flask.ext.redis import FlaskRedis
from .utils.redis_geo import GeoRedis
redis_store = FlaskRedis.from_custom_provider(GeoRedis)
from .models import db, security as security_models
from flask.ext.restplus import abort
from flask.ext.security.utils import verify_and_update_password
from flask.ext.uploads import (UploadSet, configure_uploads,
            DOCUMENTS, DATA, ARCHIVES, IMAGES)
from slacker import Slacker

user_datastore = SQLAlchemyUserDatastore(db, security_models.User,
                            security_models.Role)

valid_versions = ['1', '2']
def check_version(sender, **extra):
    if len(request.accept_mimetypes) == 0 or\
        request.accept_mimetypes[0][0] != 'application/json':
        return
    version = request.headers.get('X-VERSION', None)
    if version not in valid_versions:
        abort(404, message="Invalid version, valid versions are: {}".format(valid_versions))
    g.version = int(version)



def add_version_header(sender, response, **extra):
    response.headers['X-VERSION'] = request.headers.get('X-VERSION')

def load_user_from_request(request):
    apikey = request.headers.environ.get('HTTP_X_API_KEY', None)
    if apikey:
        u = security_models.User.query.filter_by(apikey=apikey)
        return u.first() or None
    auth = request.headers.get('Authorization')
    if not auth or auth.count(':') != 1:
        return None
    login, password = auth.split(':')
    user = user_datastore.get_user(login.strip())
    if user is None:
        return None
    if not verify_and_update_password(password.strip(), user):
        return None
    if not user.is_active():
        return None
    return user

documents = UploadSet('documents', DOCUMENTS + DATA + ARCHIVES)
images = UploadSet('images', IMAGES)

def create_app(sqlalchemy_uri=None):
    app = Flask(__name__)
    app.config.from_object('default_settings')
    if 'APITAXI_CONFIG_FILE' in os.environ:
        app.config.from_envvar('APITAXI_CONFIG_FILE')
    if not 'ENV' in app.config:
        app.logger.error('ENV is needed in the configuration')
        return None
    if app.config['ENV'] not in ('PROD', 'STAGING', 'DEV'):
        app.logger.error("""Here are the possible values for conf['ENV']:
        ('PROD', 'STAGING', 'DEV') your's is: {}""".format(app.config['env']))
        return None
    if sqlalchemy_uri:
        app.config['SQLALCHEMY_DATABASE_URI'] = sqlalchemy_uri

    db.init_app(app)
    security = Security(app, user_datastore)
    redis_store.init_app(app)
    redis_store.connection_pool.get_connection(0).can_read()
    from . import backoffice
    backoffice.init_app(app)
    from . import api
    api.init_app(app)
    from . import documentation
    documentation.init_app(app)
    Bootstrap(app)

    request_started.connect(check_version, app)
    request_finished.connect(add_version_header, app)

    configure_uploads(app, (documents, images))

    app.login_manager.request_loader(load_user_from_request)
    from . import demo
    demo.create_app(app)
    return app
