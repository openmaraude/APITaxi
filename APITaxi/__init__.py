# -*- coding: utf-8 -*-

import os

from flask import Flask, g, request_started, request_finished
from flask_uploads import configure_uploads

from APITaxi_models import db, security, HailLog
from APITaxi_utils.login_manager import init_app as init_login_manager
from APITaxi_utils.version import check_version, add_version_header

from . import api, tasks
from .api.extensions import documents
from .commands.warm_up_redis import warm_up_redis_func
from .extensions import redis_store, redis_store_saved, user_datastore


__author__ = 'Vincent Lara'
__contact__ = "vincent.lara@data.gouv.fr"
__homepage__ = "https://github.com/"
__version__ = '0.1.0'
__doc__ = 'Flask application to serve APITaxi'


def create_app():
    app = Flask(__name__)
    app.config.from_object('APITaxi.default_settings')
    if 'APITAXI_CONFIG_FILE' in os.environ:
        app.config.from_envvar('APITAXI_CONFIG_FILE')
    if 'ENV' not in app.config:
        app.logger.error('ENV is needed in the configuration')
        return None
    if app.config['ENV'] not in ('PROD', 'STAGING', 'DEV'):
        app.logger.error("""Here are the possible values for conf['ENV']:
        ('PROD', 'STAGING', 'DEV') your's is: {}""".format(app.config['env']))
        return None
    # Load configuration from environment variables
    for k in list(app.config.keys()):
        if k not in os.environ:
            continue
        app.config[k] = os.environ[k]

    db.init_app(app)
    redis_store.init_app(app)
    redis_store_saved.init_app(app)
    api.init_app(app)

    request_started.connect(check_version, app)
    request_finished.connect(add_version_header, app)

    configure_uploads(app, (documents,))
    init_login_manager(app, user_datastore, None)

    tasks.init_app(app)

    user_datastore.init_app(db, security.User, security.Role)

    @app.before_first_request
    def warm_up_redis():
        warm_up_redis_func(app, db, security.User, redis_store)

    def delete_redis_keys(response):
        if not hasattr(g, 'keys_to_delete'):
            return response
        redis_store.delete(*g.keys_to_delete)
        return response

    app.after_request_funcs.setdefault(None, []).append(
        HailLog.after_request(redis_store_saved)
    )
    app.after_request_funcs.setdefault(None, []).append(
        delete_redis_keys
    )
    return app
