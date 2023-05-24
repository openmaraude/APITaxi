import importlib
import json
import os
import pkgutil
import sys

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
from celery import Celery, Task
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_redis import FlaskRedis
from flask_security import Security, SQLAlchemyUserDatastore

import sentry_sdk
from sentry_sdk.integrations.redis import RedisIntegration

from werkzeug.exceptions import BadRequest

from APITaxi_models2 import db, Role, User

from . import commands
from . import views
from .middlewares import ForceJSONContentTypeMiddleware
from .security import auth


def handler_401():
    """Called when flask_security.login_required fails."""
    if 'X-Api-Key' not in request.headers:
        return jsonify({
            'errors': {
                '': ['Header X-Api-Key required.']
            }
        }), 401

    if 'X-Logas' in request.headers:
        msg = 'Header X-Api-Key and/or X-Logas not valid.'
    else:
        msg = 'Header X-Api-Key not valid.'

    return jsonify({
        'errors': {
            '': [msg]
        }
    }), 401


def handler_403(exc=None, func_name=None, params=None):
    """Called when flask_security.roles_accepted fails.

    exc is set if flask.abort(403) is called, and None if @roles_accepted fails.
    """
    return jsonify({
        'errors': {
            '': ['You do not have enough permissions to access this ressource.']
        }
    }), 403


def handler_404(exc):
    return jsonify({
        'errors': {
            'url': ['API endpoint not found.']
        }
    }), 404


def handler_405(exc):
    return jsonify({
        'errors': {
            'url': ['This endpoint only accepts requests of type: %s.' % ', '.join(exc.valid_methods)]
        }
    }), 405


def handler_500(exc):
    return jsonify({
        'errors': {
            '': ['Internal server error. If the problem persists, please contact the technical team.']
        }
    }), 500


@auth.error_handler
def error_handler(status_code):
    if status_code == 403:
        return handler_403()
    return handler_401()


def check_content_type():
    if request.method in ('POST', 'PUT', 'PATCH'):
        if 'application/json' not in request.headers.get('Content-Type', ''):
            return jsonify({
                'errors': {
                    '': ['%s requests require to set the Content-Type header to application/json' % request.method]
                }
            }), 400

        try:
            _ = request.get_json()
        except BadRequest:
            return jsonify({
                'errors': {
                    '': ['No data provided, or data is not valid JSON.']
                }
            }), 400

    # Continue processing
    return None


def print_url_map(url_map):
    for rule in sorted(url_map.iter_rules(), key=lambda r: r.rule):
        methods = [m for m in rule.methods if m not in ('OPTIONS', 'HEAD')]
        print(('\t%-45s -> %s' % (rule.rule, ', '.join(methods))))


def redis_init_app(app):
    redis_kwargs = {}
    # Redis listens on a unix socket in tests, no keepalive
    if not app.config.get('REDIS_URL', '').startswith('unix://'):
        redis_kwargs['socket_keepalive'] = True
    app.redis = FlaskRedis(app, **redis_kwargs)


def celery_init_app(app):
    """Configure tasks.celery:

    * read configuration from app.config and update celery config
    * create a task context so tasks can access flask.current_app

    Doing so is recommended by flask documentation:
    https://flask.palletsprojects.com/en/2.3.x/patterns/celery/
    """
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            # For a reason I haven't figured out, if I open another app context during tests,
            # Celery tasks don't see objects created by test factories
            if app.testing:
                return super().__call__(*args, **kwargs)
            else:
                with app.app_context():
                    return super().__call__(*args, **kwargs)

    # Settings list:
    # https://docs.celeryproject.org/en/stable/userguide/configuration.html
    celery_conf = {
        key[len('CELERY_'):].lower(): value
        for key, value in app.config.items()
        if key.startswith('CELERY_')
    }

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(celery_conf)
    celery_app.set_default()
    app.extensions['celery'] = celery_app
    return celery_app


def create_app():
    app = Flask(__name__, static_folder=None)
    app.wsgi_app = ForceJSONContentTypeMiddleware(app.wsgi_app)

    # Disable CORS
    CORS(app, resources={r'*': {"origins": "*"}})
    # Make /route similar to /route/
    app.url_map.strict_slashes = False

    # Load default configuration
    app.config.from_object('APITaxi2.default_settings')

    # Override default conf with environment variable APITAXI_CONFIG_FILE
    if os.getenv('APITAXI_CONFIG_FILE'):
        app.config.from_envvar('APITAXI_CONFIG_FILE')

    sentry_dsn = app.config.get('SENTRY_DSN')
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            # FlaskIntegration and Sqlalchemyintegration are enabled by default.
            integrations=[
                RedisIntegration(),
            ],
            traces_sample_rate=app.config.get('SENTRY_SAMPLE_RATE', 0.005)
        )

    db.init_app(app)
    redis_init_app(app)
    celery_init_app(app)

    # Setup flask-security (though we don't use it for authentication)
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    # register_blueprint is set to False because we do not register /login and
    # /logout views.
    app.security = Security(app, user_datastore, register_blueprint=False)

    # Load flask_security.current_user from X-API-Key HTTP header
    # XXX use Flask-HTTPAuth for now
    # app.login_manager.request_loader(security.load_user_from_api_key_header)

    app.security.unauthz_handler(handler_403)  # called if @roles_accepted fails
    app.login_manager.unauthorized_handler(handler_401)  # called if @login_required fails
    app.errorhandler(403)(handler_403)  # called by flask.abort(403)
    app.errorhandler(404)(handler_404)  # page not found
    app.errorhandler(405)(handler_405)  # method not allowed
    app.errorhandler(500)(handler_500)  # internal error (uncaught exception...)

    app.before_request(check_content_type)

    # Register views and commands blueprints dynamically: list all modules in
    # commands/ and views/, then register blueprint. Blueprint name must be
    # exactly "blueprint".
    for mod in (commands, views):
        for _imp, modname, _pkg in pkgutil.walk_packages(
            mod.__path__, mod.__name__ + '.'
        ):
            module = importlib.import_module(modname)
            blueprint = getattr(module, 'blueprint', None)

            # blueprint_enabled is a function which can be set by the view to tell
            # whether the blueprint should be active or not. By default, blueprint
            # is active.
            blueprint_enabled = getattr(module, 'blueprint_enabled', None)

            if blueprint:
                if not blueprint_enabled or blueprint_enabled(app):
                    app.register_blueprint(blueprint)

    # Only display url_map if debug and from the worker thread.
    if app.debug and os.environ.get('WERKZEUG_RUN_MAIN'):
        print('[APITaxi2 routes]')
        print_url_map(app.url_map)

    # Configuration for apispec to generate swagger documentation.
    app.apispec = APISpec(
        title='Le.taxi reference documentation',
        version='1.0.0',
        openapi_version='3.0.2',
        plugins=[FlaskPlugin(), MarshmallowPlugin()],
    )
    # Specify how to authenticate.
    api_key_scheme = {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-API-Key'
    }
    app.apispec.components.security_scheme('ApiKeyAuth', api_key_scheme)

    # Register paths for public documentation.
    # If the pydoc of the function contains the string '---', we assume it
    # should be registered.
    with app.test_request_context():
        for function in app.view_functions.values():
            if function.__doc__ and '---' in function.__doc__:
                app.apispec.path(view=function)

    @app.route('/swagger.json')
    def swagger():
        return json.dumps(app.apispec.to_dict(), indent=2)

    if os.environ.get('DEBUG_REQUESTS') in ('t', 'y', 'yes', 'true', '1') or app.config.get('DEBUG_REQUESTS'):
        @app.after_request
        def after_request_func(response):
            sys.stderr.write('============ %s %s ============\n' % (request.method, request.path))
            sys.stderr.write(str(request.headers) + '\n')
            sys.stderr.buffer.write(request.data)
            sys.stderr.write('\n')

            sys.stderr.write('............ Response ............\n')
            sys.stderr.write(response.status + '\n')
            sys.stderr.write(str(response.headers) + '\n')
            sys.stderr.buffer.write(response.data)
            sys.stderr.write('\n')
            return response

    return app
