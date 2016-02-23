# -*- coding: utf-8 -*-
from APITaxi import create_app
from flask.ext.migrate import Migrate
from APITaxi.commands import register_commands, manager

app = create_app()

manager.app = app
migrate = Migrate(app, app.extensions['sqlalchemy'].db)
register_commands(manager)

if __name__ == '__main__':
    manager.run()
