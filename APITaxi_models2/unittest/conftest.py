import hashlib
import os
import pkg_resources
import random
import signal
import sys
import tempfile
import time

import alembic
import alembic.config
import psycopg2
import pytest
import requests
import sqlalchemy
import subprocess
import testing.postgresql

import APITaxi_models2


def _run_postgresql_migrations(psql):
    """Connect to PostgreSQL and run migrations from APITaxi_models2."""
    # Create required extension on database.
    with psycopg2.connect(**psql.dsn()) as conn:
        with conn.cursor() as cursor:
            cursor.execute('CREATE EXTENSION IF NOT EXISTS postgis')
            cursor.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')
            cursor.execute('CREATE EXTENSION IF NOT EXISTS timescaledb')
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


class Postgresql(testing.postgresql.Postgresql):
    def setup(self):
        """Because we set base_dir to fasten unittests, we need to override
        setup() to check if the source and destination given to shutil.copytree
        are not the same.

        This is a workaround for https://github.com/tk0miya/testing.common.database/issues/24
        """
        data_dir = self.get_data_directory()
        if self.settings['copy_data_from'] == data_dir:
            return
        return super().setup()

    def initialize_database(self):
        super().initialize_database()
        # timescaledb must be preloaded
        with open('%s/postgresql.conf' % self.get_data_directory(), 'a') as f:
            f.write("shared_preload_libraries = 'timescaledb'\n")


class PostgresqlFactory(testing.postgresql.PostgresqlFactory):
    target_class = Postgresql


def get_hash_from_migrations_content():
    """Generate a stable hash from the content of all migration files in
    APITaxi_models2/migrations/versions.

    If any migration content changes, or if migrations are added or removed,
    the hash will be different.
    """
    migrations_dir = pkg_resources.resource_filename(
        APITaxi_models2.__name__,
        'migrations/'
    )
    versions_dir = os.path.join(migrations_dir, 'versions')
    h = hashlib.md5()

    for filename in os.listdir(versions_dir):
        path = os.path.join(versions_dir, filename)
        # Ignore if file is not migration file
        if not path.endswith('.py'):
            continue
        # Read file content to update hash
        with open(path, 'rb') as handle:
            while True:
                data = handle.read(4096)
                if not data:
                    break
                h.update(data)
    return h.hexdigest()


@pytest.fixture(scope='session')
def postgresql():
    """Load PostgreSQL. Requires to have postgis install on the system to run
    migrations.

    The "session" scope means the database is only started once for all tests.
    """
    # Save database in base_dir, so next invokations of unittests will be
    # faster. If migrations change, base_dir will be different.
    base_dir = '/tmp/tests_%s' % get_hash_from_migrations_content()

    if os.path.exists(base_dir):
        sys.stderr.write('\n!!! Reuse test database %s from previous run !!!\n' % base_dir)

    factory = PostgresqlFactory(
        cache_initialized_db=True,
        on_initialized=_run_postgresql_migrations,
        base_dir=base_dir
    )

    psql = factory()
    yield psql
    factory.clear_cache()


@pytest.fixture
def postgresql_empty():
    """Returns a function to remove all data from database. Useful to get a
    clean state after running a unittest."""
    def clean_db():
        APITaxi_models2.db.session.execute(sqlalchemy.text('SET CONSTRAINTS ALL DEFERRED'))
        inspector = sqlalchemy.inspect(APITaxi_models2.db.engine)
        for table in reversed(APITaxi_models2.db.metadata.sorted_tables):
            # Ignore tables declared as SQLALchemy models but not present in
            # alembic migrations.
            if not inspector.has_table(table.name):
                continue
            APITaxi_models2.db.session.execute(table.delete())
        APITaxi_models2.db.session.commit()
        APITaxi_models2.db.engine.dispose()
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

    def _add_query(self, conn, clause_element, multiparams, params, execution_options, result):
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


@pytest.fixture(scope='session')
def redis_server():
    with tempfile.TemporaryDirectory() as tmpdir:
        redis_config_name = os.path.join(tmpdir, 'redis.conf')
        socket_file = os.path.join(tmpdir, 'redis.sock')
        pid_file = os.path.join(tmpdir, 'redis.pid')

        with open(redis_config_name, 'w+') as handle:
            handle.write('''
# Don't listen on TCP
port 0
unixsocket %(socket_file)s
unixsocketperm 700
daemonize yes
pidfile %(pid_file)s
loglevel notice
''' % {'socket_file': socket_file, 'pid_file': pid_file})

        subprocess.check_call(
            ['redis-server', redis_config_name]
        )

        yield socket_file

        # Wait for pid file to exist
        while True:
            try:
                with open(pid_file) as handle:
                    pid = int(handle.read().strip())
                    break
            except FileNotFoundError:
                time.sleep(.1)

        os.kill(pid, signal.SIGKILL)
