from logging.config import fileConfig
import os
import re
import sys

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name:
    fileConfig(config.config_file_name)
# config_file_name is not set during unittests. Setup logging using
# ../alembic.ini.
else:
    fileConfig(os.path.join(os.path.dirname(__file__), '../alembic.ini'))

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from APITaxi_models2 import db
target_metadata = db.metadata


def load_config():
    """Load SQLALCHEMY_DATABASE_URI from APITAXI_CONFIG_FILE settings. We do
    not import the file because settings file could import some modules which
    require to have an application context.
    """
    conf_file = os.getenv('APITAXI_CONFIG_FILE')
    if not conf_file:
        sys.stderr.write('APITAXI_CONFIG_FILE not defined. Fallback to '
                         'PostgreSQL configuration from alembic.ini\n')
        return

    with open(conf_file) as handle:
        for line in handle:
            match = re.match(r'SQLALCHEMY_DATABASE_URI\s*=\s*[\'"]([^\'"]*)', line)
            if match:
                url = match.groups()[0]
                config.set_main_option('sqlalchemy.url', url)
                return
    sys.stderr.write('Unable to find SQLALCHEMY_DATABASE_URI conf '
                     'variable in %s' % conf_file)

load_config()

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


excluded_tables = [t.strip() for t in config.get_section('alembic:exclude').get('tables', '').split(',')]


def include_object(object_, name, type_, reflected, compare_to):
    if type_ == 'table' and name in excluded_tables:
        sys.stdout.write('Table "%s" is excluded and will be ignored.\n' % name)
        return False
    return True


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, include_object=include_object
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
