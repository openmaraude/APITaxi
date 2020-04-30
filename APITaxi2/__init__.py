import importlib
import os
import pkgutil

from flask import Flask, jsonify
from flask_redis import FlaskRedis
from flask_security import Security, SQLAlchemyUserDatastore

from APITaxi_models2 import db, Role, User

from . import views


__author__ = 'Julien Castets'
__contact__ = 'julien.castets@beta.gouv.fr'
__homepage__ = 'https://github.com/openmaraude/APITaxi'
__version__ = '0.1.0'
__doc__ = 'REST API of le.taxi'


redis_client = FlaskRedis()


def load_user_from_api_key_header(request):
    """Callback to extract X-Api-Key header from the request and get user."""
    value = request.headers.get('X-Api-Key')
    if value:
        user = User.query.filter_by(apikey=value).first()
        if user:
            return user
    return None


def unauthorized_handler():
    """Called when flask_security.login_required fails."""
    return jsonify({
        'error': 'This endpoint requires authentication. Did you provide a valid X-Api-Key HTTP header?'
    }), 401


def permission_denied_handler():
    """Called when flask_security.roles_accepted fails."""
    return jsonify({
        'error': 'You do not have enough permissions to access this ressource.'
    }), 403


def handler_500(exc):
    return jsonify({
        'error': 'Internal server error. If the problem persists, please contact the technical team.'
    }), 500


def handler_404(exc):
    return jsonify({
        'error': 'Ressource not found.'
    }), 404


def print_url_map(url_map):
    for rule in sorted(url_map.iter_rules(), key=lambda r: r.rule):
        methods = [m for m in rule.methods if m not in('OPTIONS', 'HEAD')]
        print(('\t%-45s -> %s' % (rule.rule, ', '.join(methods))))


def create_app():
    app = Flask(__name__)
    app.url_map.strict_slashes = False

    # Load default configuration
    app.config.from_object('APITaxi2.default_settings')

    # Override default conf with environment variable APITAXI_CONFIG_FILE
    if 'APITAXI_CONFIG_FILE' not in os.environ:
        raise RuntimeError('APITAXI_CONFIG_FILE environment variable required')
    app.config.from_envvar('APITAXI_CONFIG_FILE')

    db.init_app(app)
    redis_client.init_app(app)

    # Setup flask-security
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security = Security()
    # register_blueprint is set to False because we do not register /login and
    # /logout views.
    security_state = security.init_app(app, user_datastore, register_blueprint=False)
    security_state.unauthorized_handler(permission_denied_handler)

    app.login_manager.unauthorized_handler(unauthorized_handler)
    app.login_manager.request_loader(load_user_from_api_key_header)

    app.errorhandler(404)(handler_404)
    app.errorhandler(500)(handler_500)

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
