# -*- coding: utf8 -*-
from backoffice_operateurs import manager, app, db
from flask.ext.migrate import Migrate, MigrateCommand
from backoffice_operateurs.commands import *
from backoffice_operateurs.views import *

migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
