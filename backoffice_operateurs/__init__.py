# -*- coding: utf8 -*-
VERSION = (0, 1, 0)
__author__ = 'Vincent Lara'
__contact__ = "vincent.lara@data.gouv.fr"
__homepage__ = "https://github.com/"
__version__ = ".".join(map(str, VERSION))


from flask import Flask
from flask.ext.security import Security, SQLAlchemyUserDatastore
from flask.ext.script import Manager
from flask_bootstrap import Bootstrap
import os
from models import db, security as security_models, taxis as taxis_models,\
    administrative as administrative_models

app = Flask(__name__)
app.config.from_object('default_settings')
if 'BO_OPERATEURS_CONFIG_FILE' in os.environ:
    app.config.from_envvar('BO_OPERATEURS_CONFIG_FILE')

db.init_app(app)

user_datastore = SQLAlchemyUserDatastore(db, security_models.User,
                            security_models.Role)
security = Security(app, user_datastore)

from views import ads
from views import conducteur
from views import zupc
from views import home

app.register_blueprint(ads.mod)
app.register_blueprint(conducteur.mod)
app.register_blueprint(zupc.mod)
app.register_blueprint(home.mod)

Bootstrap(app)

manager = Manager(app)
