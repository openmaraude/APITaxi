# -*- coding: utf8 -*-
VERSION = (0, 1, 0)
__author__ = 'Vincent Lara'
__contact__ = "vincent.lara@data.gouv.fr"
__homepage__ = "https://github.com/"
__version__ = ".".join(map(str, VERSION))


from flask import Flask, make_response, jsonify, render_template
from flask.ext.security import Security, SQLAlchemyUserDatastore
from flask.ext.script import Manager
from flask.ext.security.utils import verify_and_update_password
from flask_bootstrap import Bootstrap
import os
from models import db
from models import security as security_models, taxis as taxis_models,\
    administrative as administrative_models, hail as hail_model
from flask.ext.restplus import Api, apidoc, abort
from flask.ext.redis import FlaskRedis



app = Flask(__name__)
app.config.from_object('default_settings')
if 'APITAXI_CONFIG_FILE' in os.environ:
    app.config.from_envvar('APITAXI_CONFIG_FILE')

db.init_app(app)

user_datastore = SQLAlchemyUserDatastore(db, security_models.User,
                            security_models.Role)
security = Security(app, user_datastore)
api = Api(app, ui=False, catch_all_404s=True)
ns_administrative = api.namespace('administrative',
        description="Administrative APIs", path='/')
ns_hail = api.namespace('hails', description="Hail API")
ns_taxis = api.namespace('taxis', description="Taxi API")

from .utils.redis_geo import GeoRedis
redis_store = FlaskRedis.from_custom_provider(GeoRedis, app)

from .views import ads
from .views import drivers
from .views import zupc
from .views import home
from .views import hail
from .views import vehicle
from .views import taxi

@apidoc.apidoc.route('/doc/', endpoint='doc')
def swagger_ui():
    return render_template('swagger/index.html')
    #return apidoc.ui_for(api)


app.register_blueprint(ads.mod)
app.register_blueprint(drivers.mod)
app.register_blueprint(zupc.mod)
app.register_blueprint(home.mod)
app.register_blueprint(apidoc.apidoc)

@api.representation('text/html')
def output_html(data, code=200, headers=None):
    if type(data) is dict:
        data = jsonify(data)
    resp = make_response(data.encode('latin-1'), code)
    resp.headers.extend(headers or {})
    resp.headers['Content-Type'] = 'text/html; charset=latin-1'
    return resp


@app.login_manager.request_loader
def load_user_from_request(request):
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

Bootstrap(app)

manager = Manager(app)
