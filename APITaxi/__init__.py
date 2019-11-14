# -*- coding: utf-8 -*-

import os

from flask import Flask, g, request_started, request_finished
from flask_restplus import abort
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


def load_configuration(app):
    """Load application configuration:

    - from default_settings.py
    - from the settings file set in the environment variable
      APITAXI_CONFIG_FILE
    - from variables set in environment
    """
    app.config.from_object('APITaxi.default_settings')

    if 'APITAXI_CONFIG_FILE' in os.environ:
        app.config.from_envvar('APITAXI_CONFIG_FILE')

    if 'ENV' not in app.config:
        raise ValueError('Configuration variable ENV is required')

    valid_env = ('PROD', 'STAGING', 'DEV')
    if app.config['ENV'] not in valid_env:
        raise ValueError('ENV {} invalid, must be any of {}'.format(
            app.config['ENV'], valid_env
        ))

    for param in app.config:
        if param not in os.environ:
            continue
        app.config[param] = os.environ[param]

    app.url_map.strict_slashes = False


def print_url_map(url_map):
    for rule in sorted(url_map.iter_rules(), key=lambda r: r.rule):
        methods = [m for m in rule.methods if m not in('OPTIONS', 'HEAD')]
        print(('\t%-45s -> %s' % (rule.rule, ', '.join(methods))))


def unauthorized():
    """By default, @login_required returns HTTP/301 HTML response to redirect
    the browser to the login form. Since we are in the context of an API,
    clients are expecting a JSON response.
    """
    abort(401, error='You are not logged in. Please provide a valid X-Api-Key header.')


def create_app():
    app = Flask(__name__)

    load_configuration(app)

    db.init_app(app)
    redis_store.init_app(app)
    redis_store_saved.init_app(app)
    api.init_app(app)

    # Only display url_map if debug and from the worker thread.
    if app.debug and os.environ.get('WERKZEUG_RUN_MAIN'):
        print_url_map(app.url_map)

    request_started.connect(check_version, app)
    request_finished.connect(add_version_header, app)

    configure_uploads(app, (documents,))

    init_login_manager(app, user_datastore, None)
    app.login_manager.unauthorized_handler(unauthorized)

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
