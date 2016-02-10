# -*- coding: utf-8 -*-
from ..api import api

def init_app(app):
    from . import (ads, drivers, home, user_key, vehicle, zupc, profile,
            documents, dash)
    app.register_blueprint(ads.mod)
    app.register_blueprint(drivers.mod)
    app.register_blueprint(home.mod)
    app.register_blueprint(user_key.mod)
    app.register_blueprint(vehicle.mod)
    app.register_blueprint(zupc.mod)
    app.register_blueprint(profile.mod)
    app.register_blueprint(documents.mod)
    app.register_blueprint(dash.mod)
