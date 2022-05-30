# flake8: noqa
from dataclasses import dataclass
import os

import flask
import pytest

from influxdb import InfluxDBClient

import APITaxi_models2

from APITaxi_models2.unittest.factories import (
    RoleFactory,
    RolesUsersFactory,
    UserFactory
)

# We have to import postgresql, postgresql_empty and redis_server even if they
# are unused because otherwise they cannot be used as dependencies by fixtures
# below.
from APITaxi_models2.unittest.conftest import (
    postgresql,
    postgresql_empty,
    influx_server,
    redis_server,
    SQLAlchemyQueriesTracker,
)

import APITaxi2


@pytest.fixture
def app(tmp_path, postgresql, postgresql_empty, redis_server, influx_server):
    settings_file = tmp_path / 'settings.py'
    settings_file.write_text('''
SQLALCHEMY_DATABASE_URI = '%(database)s'
SECRET_KEY = 's3cr3t'
REDIS_URL = '%(redis)s'
INFLUXDB_DATABASE = '%(influx_database)s'
INFLUXDB_PORT = %(influx_port)s
SECURITY_PASSWORD_HASH = 'plaintext'
DEBUG = True
CONSOLE_URL = 'http://console'
''' % {
        'database': postgresql.url(),
        'redis': 'unix://%s' % redis_server,
        'influx_database': influx_server['database'],
        'influx_port': influx_server['port']
    })
    os.environ['APITAXI_CONFIG_FILE'] = settings_file.as_posix()

    app = APITaxi2.create_app()

    with app.app_context():
        yield app

        # Remove all data from database for next test.
        postgresql_empty()
        # Remove all from redis.
        app.redis.flushall()
        # Remove all from influx.
        InfluxDBClient(
            port=influx_server['port'],
            database=influx_server['database']
        ).query('DROP SERIES FROM /.*/')


@dataclass
class Client:
    client: flask.testing.FlaskClient
    user: APITaxi_models2.User = None


def _create_client(app, roles):
    create_user = roles is not None

    if create_user:
        user = UserFactory()
        for role_name in roles:
            role = RoleFactory(name=role_name)
            role_user = RolesUsersFactory(role=role, user=user)

    with app.test_client() as client:
        if not create_user:
            yield Client(client=client)
        else:
            # Setup X-Api-Key HTTP header
            client.environ_base['HTTP_X_API_KEY'] = user.apikey
            yield Client(user=user, client=client)


@pytest.fixture
def all_roles(app):
    yield from _create_client(app, ['admin', 'moteur', 'operateur'])


@pytest.fixture
def no_roles(app):
    """Authenticated user without any roles."""
    yield from _create_client(app, [])


@pytest.fixture
def anonymous(app):
    yield from _create_client(app, None)


@pytest.fixture
def admin(app):
    yield from _create_client(app, ['admin'])


@pytest.fixture
def moteur(app):
    yield from _create_client(app, ['moteur'])


@pytest.fixture
def operateur(app):
    yield from _create_client(app, ['operateur'])


@pytest.fixture
def QueriesTracker():
    return lambda: SQLAlchemyQueriesTracker(APITaxi_models2.db.engine)
