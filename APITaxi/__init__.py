# -*- coding: utf-8 -*-
VERSION = (0, 1, 0)
__author__ = 'Vincent Lara'
__contact__ = "vincent.lara@data.gouv.fr"
__homepage__ = "https://github.com/"
__version__ = ".".join(map(str, VERSION))


from flask import Flask, request_started, request, request_finished, g
from flask_bootstrap import Bootstrap
import os
from flask.ext.redis import FlaskRedis
from flask.ext.restplus import abort
from flask.ext.uploads import (UploadSet, configure_uploads,
            DOCUMENTS, DATA, ARCHIVES, IMAGES)
from .utils.request_wants_json import request_wants_json
from flask_sqlalchemy import models_committed


valid_versions = ['1', '2']
def check_version(sender, **extra):
    if not request_wants_json():
        return
    if request.url_rule is None:
        return
    endpoint = request.url_rule.endpoint
    if endpoint == 'api.specs' or endpoint == 'static' or endpoint.startswith('js_bo'):
        return
    version = request.headers.get('X-VERSION', None)
    if version not in valid_versions:
        abort(404, message="Invalid version, valid versions are: {}".format(valid_versions))
    g.version = int(version)



def add_version_header(sender, response, **extra):
    response.headers['X-VERSION'] = request.headers.get('X-VERSION')

def commit_signal(sender, changes):
    for model, change in changes:
        if not hasattr(model, 'cache'):
            continue
        model.cache._flush_all(model)

def create_app(sqlalchemy_uri=None):
    from .extensions import (db, redis_store, regions, configure_uploads,
            documents, images)
    app = Flask(__name__)
    app.config.from_object('APITaxi.default_settings')
    if 'APITAXI_CONFIG_FILE' in os.environ:
        app.config.from_envvar('APITAXI_CONFIG_FILE')
    if not 'ENV' in app.config:
        app.logger.error('ENV is needed in the configuration')
        return None
    if app.config['ENV'] not in ('PROD', 'STAGING', 'DEV'):
        app.logger.error("""Here are the possible values for conf['ENV']:
        ('PROD', 'STAGING', 'DEV') your's is: {}""".format(app.config['env']))
        return None
    #Load configuration from environment variables
    for k in app.config.keys():
        if not k in os.environ:
            continue
        app.config[k] = os.environ[k]
    if sqlalchemy_uri:
        app.config['SQLALCHEMY_DATABASE_URI'] = sqlalchemy_uri

    db.init_app(app)
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
    from .utils.login_manager import init_app as init_login_manager
    init_login_manager(app)
    from . import demo
    demo.create_app(app)
    for region in regions.values():
        if not region.is_configured:
            region.configure(app.config['DOGPILE_CACHE_BACKEND'])
    from . import tasks
    tasks.init_app(app)

    models_committed.connect_via(app)(commit_signal)
    return app
