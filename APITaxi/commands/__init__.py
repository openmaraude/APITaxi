from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.script.commands import ShowUrls

manager = Manager()

def register_commands(manager):
    from .create_user import (create_operateur, create_moteur, create_admin,
              create_mairie)
    manager.add_command('db', MigrateCommand)
    manager.add_command('urls', ShowUrls)

