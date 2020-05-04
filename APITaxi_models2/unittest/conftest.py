import os
import pkg_resources

import alembic, alembic.config
from flask_security import  SQLAlchemyUserDatastore
import psycopg2
import pytest
from pytest_factoryboy import register
import testing.postgresql

import APITaxi_models2

from . import factories


# Create fixtures from factories. The name of the fixture is the snake case of
# the class. For example, VehicleFactory corresponds to the fixture
# vehicle_factory.
register(factories.ADSFactory)
register(factories.DepartementFactory)
register(factories.DriverFactory)
register(factories.HailFactory)
register(factories.TaxiFactory)
register(factories.UserFactory)
register(factories.VehicleFactory)
register(factories.ZUPCFactory)


def _run_postgresql_migrations(psql):
    """Connect to PostgreSQL and run migrations from APITaxi_models2."""
    # Create required extension on database.
    with psycopg2.connect(**psql.dsn()) as conn:
        with conn.cursor() as cursor:
            cursor.execute('CREATE EXTENSION postgis')
        conn.commit()

    migrations_dir = pkg_resources.resource_filename(
        APITaxi_models2.__name__,
        'migrations'
    )

    # Build Alembic configuration to run migrations
    alembic_cfg = alembic.config.Config()
    alembic_cfg.set_main_option('sqlalchemy.url', psql.url())
    alembic_cfg.set_main_option('script_location', migrations_dir)

    # APITaxi_models2/migrations/env.py loads APITAXI_CONFIG_FILE to get the
    # database dsn. If the variable doesn't exist, it uses alembic
    # configuration.
    # If the developer runs unittests manually and APITAXI_CONFIG_FILE is set,
    # we do not want to run unittests against the development database, so
    # let's remove the environ variable.
    if 'APITAXI_CONFIG_FILE' in os.environ:
        del os.environ['APITAXI_CONFIG_FILE']

    # Run migrations
    alembic.command.upgrade(alembic_cfg, 'head')


@pytest.fixture(scope='session')
def postgresql():
    """Load PostgreSQL. Requires to have postgis install on the system to run
    migrations.

    The "session" scope means the database is only started once for all tests.
    """
    factory = testing.postgresql.PostgresqlFactory(
        cache_initialized_db=True,
        on_initialized=_run_postgresql_migrations
    )

    psql = factory()
    yield psql
    factory.clear_cache()


@pytest.fixture
def postgresql_empty():
    """Returns a function to remove all data from database. Useful to get a
    clean state after running a unittest."""
    def clean_db():
        for table in reversed(APITaxi_models2.db.metadata.sorted_tables):
            APITaxi_models2.db.session.execute(table.delete())
        APITaxi_models2.db.session.commit()
    return clean_db
