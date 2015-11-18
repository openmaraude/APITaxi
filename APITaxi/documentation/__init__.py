# -*- coding: utf-8 -*-

def init_app(app):
    from . import index
    app.register_blueprint(index.mod)
    from . import moteur
    app.register_blueprint(moteur.mod)
    from . import operateur
    app.register_blueprint(operateur.mod)
    from . import reference
    app.register_blueprint(reference.mod)
    from . import examples
    app.register_blueprint(examples.mod)
