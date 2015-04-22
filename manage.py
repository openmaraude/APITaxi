# -*- coding: utf8 -*-
from APITaxi import manager, app, db
from flask.ext.migrate import Migrate, MigrateCommand
from APITaxi.commands import *

migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
