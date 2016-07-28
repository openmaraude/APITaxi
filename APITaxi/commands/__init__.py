# -*- coding: utf-8 -*-
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from flask_script.commands import ShowUrls

manager = Manager()

def register_commands(manager):
    from .create_user import (create_operateur, create_moteur, create_admin,
              create_mairie)
    from .create_influx_db import create_influx_db
    manager.add_command('db', MigrateCommand)
    manager.add_command('urls', ShowUrls)
    from .load_zupc import load_zupc, add_airport_zupc
    from .active_tasks import active_tasks
    from .export_taxis import export_taxis
    from .import_zupc import import_zupc
    from .warm_up_redis import warm_up_redis
