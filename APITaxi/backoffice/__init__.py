from ..api import api

ns_administrative = api.namespace('administrative',
        description="Administrative APIs", path='/')

def init_app(app):
    from . import ads, drivers, home, user_key, vehicle, zupc
    app.register_blueprint(ads.mod)
    app.register_blueprint(drivers.mod)
    app.register_blueprint(home.mod)
    app.register_blueprint(user_key.mod)
    app.register_blueprint(vehicle.mod)
    app.register_blueprint(zupc.mod)
