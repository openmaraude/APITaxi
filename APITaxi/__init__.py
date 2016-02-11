# -*- coding: utf-8 -*-
VERSION = (0, 1, 0)
__author__ = 'Vincent Lara'
__contact__ = "vincent.lara@data.gouv.fr"
__homepage__ = "https://github.com/"
__version__ = ".".join(map(str, VERSION))


from flask import Flask, request_started, request, request_finished, g
from flask_bootstrap import Bootstrap
import os
from flask.ext.restplus import abort
from APITaxi_utils.request_wants_json import request_wants_json
from flask.ext.dogpile_cache import DogpileCache


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

def create_app(sqlalchemy_uri=None):
    from .extensions import redis_store, user_datastore
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

    from APITaxi_models import db
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

    from flask.ext.uploads import configure_uploads
    from .api.extensions import documents
    from .backoffice.extensions import images
    configure_uploads(app, (documents, images))
    from APITaxi_utils.login_manager import init_app as init_login_manager
    from .backoffice.forms.login import LoginForm
    init_login_manager(app, user_datastore, LoginForm)
    from . import demo
    demo.create_app(app)

    from . import tasks
    tasks.init_app(app)

    from APITaxi_models import security
    user_datastore.init_app(db, security.User, security.CachedUser,
            security.Role)
    cache = DogpileCache()
    cache.init_app(app)

    @app.before_first_request
    def warm_up_redis():
        not_available = set()
        available = set()
        cur = db.session.connection().connection.cursor()
        cur.execute("""
        SELECT taxi.id AS taxi_id, vd.status, vd.added_by FROM taxi
        LEFT OUTER JOIN vehicle ON vehicle.id = taxi.vehicle_id
        LEFT OUTER JOIN vehicle_description AS vd ON vehicle.id = vd.vehicle_id
        """)
        users = {u.id: u.email for u in security.User.query.all()}
        for taxi_id, status, added_by in cur.fetchall():
            user = users.get(added_by)
            taxi_id_operator = "{}:{}".format(taxi_id, user)
            if status == 'free':
                available.add(taxi_id_operator)
            else:
                not_available.add(taxi_id_operator)
        to_remove = list()
        cursor, keys = redis_store.sscan(app.config['REDIS_NOT_AVAILABLE'], 0)
        keys = set(keys)
        while cursor != 0:
            to_remove.extend(keys.intersection(available))
            not_available.difference_update(keys)
            cursor, keys = redis_store.sscan(app.config['REDIS_NOT_AVAILABLE'], 
                    cursor)
            keys = set(keys)
        if len(to_remove) > 0:
            redis_store.srem(app.config['REDIS_NOT_AVAILABLE'], to_remove)
        if len(not_available) > 0:
            redis_store.sadd(app.config['REDIS_NOT_AVAILABLE'], *not_available)


    return app
