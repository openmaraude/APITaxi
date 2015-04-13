# -*- coding: utf8 -*-
VERSION = (0, 1, 0)
__author__ = 'Vincent Lara'
__contact__ = "vincent.lara@data.gouv.fr"
__homepage__ = "https://github.com/"
__version__ = ".".join(map(str, VERSION))


from flask import Flask, make_response
from flask.ext.security import Security, SQLAlchemyUserDatastore
from flask.ext.script import Manager
from flask.ext.security.utils import verify_and_update_password
from flask.ext import restful
from flask_bootstrap import Bootstrap
import os
from models import db
from models import security as security_models, taxis as taxis_models,\
    administrative as administrative_models
from flask.ext.restplus import Api

app = Flask(__name__)
app.config.from_object('default_settings')
if 'BO_OPERATEURS_CONFIG_FILE' in os.environ:
    app.config.from_envvar('BO_OPERATEURS_CONFIG_FILE')

db.init_app(app)

user_datastore = SQLAlchemyUserDatastore(db, security_models.User,
                            security_models.Role)
security = Security(app, user_datastore)
api = Api(app)
api.model(taxis_models.ADS, taxis_models.ADS.marshall_obj())
ns = api.namespace('ADS', description="Description ADS")

from views import ads
from views import conducteur
from views import zupc
from views import home

app.register_blueprint(ads.mod)
app.register_blueprint(conducteur.mod)
app.register_blueprint(zupc.mod)
app.register_blueprint(home.mod)

@api.representation('text/html')
def output_html(data, code=200, headers=None):
    resp = make_response(data, code)
    resp.headers.extend(headers or {})
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
