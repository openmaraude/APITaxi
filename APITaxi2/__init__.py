import importlib
import os
import pkgutil

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_influxdb import InfluxDB
from flask_redis import FlaskRedis
from flask_security import Security, SQLAlchemyUserDatastore

from werkzeug.exceptions import BadRequest

from APITaxi_models2 import db, Role, User

from . import views
from .tasks import celery


__author__ = 'Julien Castets'
__contact__ = 'julien.castets@beta.gouv.fr'
__homepage__ = 'https://github.com/openmaraude/APITaxi'
__version__ = '0.1.0'
__doc__ = 'REST API of le.taxi'


def load_user_from_api_key_header(request):
    """Callback to extract X-Api-Key header from the request and get user."""
    value = request.headers.get('X-Api-Key')
    if value:
        user = User.query.filter_by(apikey=value).first()
        if user:
            return user
    return None


def handler_401():
    """Called when flask_security.login_required fails."""
    if 'X-Api-Key' not in request.headers:
        return jsonify({
            'errors': {
                '': ['The header X-Api-Key is required.']
            }
        }), 401
    return jsonify({
        'errors': {
            '': ['The X-Api-Key provided is not valid.']
        }
    }), 401


def handler_403(exc=None):
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


def handler_500(exc):
    return jsonify({
        'errors': {
            '': ['Internal server error. If the problem persists, please contact the technical team.']
        }
    }), 500


def check_content_type():
    if request.method in ('POST', 'PUT', 'PATCH'):
        if request.headers.get('Content-Type', '').lower() != 'application/json':
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


def configure_celery(flask_app):
    """Configure tasks.celery:

    * read configuration from flask_app.config and update celery config
    * create a task context so tasks can access flask.current_app

    Doing so is recommended by flask documentation:
    https://flask.palletsprojects.com/en/1.1.x/patterns/celery/
    """
    # Settings list:
    # https://docs.celeryproject.org/en/stable/userguide/configuration.html
    celery_conf = {
        key[len('CELERY_'):].lower(): value
        for key, value in flask_app.config.items()
        if key.startswith('CELERY_')
    }
    celery.conf.update(celery_conf)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask


def create_app():
    app = Flask(__name__, static_folder=None)
    # Disable CORS
    cors = CORS(app, resources={r'*': {"origins": "*"}})
    # Make /route similar to /route/
    app.url_map.strict_slashes = False

    # Load default configuration
    app.config.from_object('APITaxi2.default_settings')

    # Override default conf with environment variable APITAXI_CONFIG_FILE
    if 'APITAXI_CONFIG_FILE' not in os.environ:
        raise RuntimeError('APITAXI_CONFIG_FILE environment variable required')
    try:
        app.config.from_envvar('APITAXI_CONFIG_FILE')
    except FileNotFoundError:
        app.logger.warning('File %s does not exist, skip loading' % os.getenv('APITAXI_CONFIG_FILE'))

    db.init_app(app)
    app.influx = InfluxDB(app)
    app.redis = FlaskRedis(app)
    configure_celery(app)

    # Setup flask-security
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security = Security()
    # register_blueprint is set to False because we do not register /login and
    # /logout views.
    security_state = security.init_app(app, user_datastore, register_blueprint=False)

    # Load flask_security.current_user from X-API-Key HTTP header
    app.login_manager.request_loader(load_user_from_api_key_header)

    security_state.unauthorized_handler(handler_403)  # called if @roles_accepted fails
    app.login_manager.unauthorized_handler(handler_401)  # called if @login_required fails
    app.errorhandler(403)(handler_403)  # called by flask.abort(403)
    app.errorhandler(404)(handler_404)  # page not found
    app.errorhandler(500)(handler_500)  # internal error (uncaught exception...)

    app.before_request(check_content_type)

    # Register blueprints dynamically: list all modules in views/ and register
    # blueprint. Blueprint's name must be exactly "blueprint".
    for _imp, modname, _pkg in pkgutil.walk_packages(
        views.__path__, views.__name__ + '.'
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

    return app
