import os
import pkg_resources
import sys

import alembic, alembic.config
from flask_security import  SQLAlchemyUserDatastore
import psycopg2
import pytest
from pytest_factoryboy import register
import sqlalchemy
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


class SQLAlchemyQueriesTracker:
    """Context manager to count the number of SQLAlchemy database hits.

    SQLAlchemy events are global to the connection, so concurrent usages of
    this context manager won't yield expected results.
    """
    def __init__(self, conn):
        self.conn = conn
        self.count = 0
        self.queries = []
        sqlalchemy.event.listen(self.conn, 'after_execute', self._add_query)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        sqlalchemy.event.remove(self.conn, 'after_execute', self._add_query)

    def _add_query(self, conn, clause_element, multiparams, params, result):
        self.queries.append({
            'clause': clause_element,
            'params': params,
            'result': result,
        })
        self.count += 1

    def debug(self, output=sys.stderr):
        """Outputs queries on stderr. Useful for debugging when you don't know
        where queries come from.
        """
        output.write('======== %s SQL Queries executed ========\n' % str(self.count))
        for idx, query in enumerate(self.queries):

            if idx:
                output.write('\n')

            output.write('--- query %s ---\n' % str(idx + 1))
            output.write('%s\n' % query['clause'])
            if query['params']:
                output.write('\twith params:\n')
                for param in query['params']:
                    output.write('\t\t%s\n' % param)
            output.write('\n')
        output.write('======== end of queries ========\n')
