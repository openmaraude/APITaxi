from flask import Flask, Blueprint, current_app

demoblue = Blueprint('demo', __name__)

@demoblue.route('/demo/map')
def demo_map():
    return current_app.send_static_file('demo/map.html')


def create_app(app):
    app.register_blueprint(demoblue)
