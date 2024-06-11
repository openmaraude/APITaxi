from setuptools import find_packages, setup
import os
import re


PACKAGE = 'APITaxi'

DEPENDENCIES = [
    'alembic==1.13.1',
    'apispec[validation,marshmallow]==6.6.1',
    'apispec-webframeworks==1.1.0',
    'bcrypt==4.1.3',
    'celery==5.4.0',
    'Flask==3.0.3',
    'Flask-Cors==4.0.1',
    'Flask-HTTPAuth==4.8.0',
    'Flask-Login==0.6.3',
    'Flask-Migrate==4.0.7',
    'Flask-Principal==0.4.0',
    'Flask-Redis==0.4.0',
    'Flask-Security-Too[common]==5.4.3',
    'Flask-SQLAlchemy==3.1.1',
    'GeoAlchemy2==0.15.1',
    'geopy==2.4.1',
    'hiredis==2.3.2',
    'openapi-spec-validator==0.7.1',
    'prettytable==3.10.0',
    # While psycopg 3 is compatible, SQLAlchemy doesn't make it convenient
    # Check for a transparent shapely integration
    'psycopg2==2.9.9',
    'pytz',
    'redis==5.0.5',
    'requests==2.32.3',
    'sentry-sdk[flask]==2.5.1',
    'Shapely==2.0.4',
    'shortuuid==1.0.11',
    'SQLAlchemy==2.0.30',
    'SQLAlchemy-Defaults',
    'SQLAlchemy-Utils',
    'tzdata',
    'watchdog[watchmedo]==4.0.1',
    'Werkzeug==3.0.3',
]

TEST_DEPENDENCIES = [
    'pytest>=7.4.4',
    'pytest-celery',
    'pytest-factoryboy',
    'testing.postgresql',
]


def get_pkgvar(name):
    """Get the value of :param name: from __init__.py.

    The package cannot be imported since dependencies might not be installed
    yet."""
    here = os.path.abspath(os.path.dirname(__file__))
    init_path = os.path.join(here, PACKAGE, '__init__.py')

    # Cache file content into get_pkgvar.init_content to avoid reading the
    # __init__.py file several times.
    if not hasattr(get_pkgvar, 'init_content'):
        with open(init_path) as handle:
            get_pkgvar.init_content = handle.read().splitlines()

    for line in get_pkgvar.init_content:
        res = re.search(r'^%s\s*=\s*["\'](.*)["\']' % name, line)
        if res:
            return res.groups()[0]

    raise ValueError('%s not found in %s' % (name, init_path))


setup(
    name=PACKAGE,
    version=get_pkgvar('__version__'),
    description=get_pkgvar('__doc__'),
    url=get_pkgvar('__homepage__'),
    author=get_pkgvar('__author__'),
    author_email=get_pkgvar('__contact__'),
    license='MIT',
    classifiers=[
        'Development Status :: 4 Beta',
        'Intended Audience :: Developpers',
        'Programming Language :: Python :: 3'
    ],
    extras_require={
        'tests': TEST_DEPENDENCIES,
    },
    keywords='taxi transportation',
    packages=find_packages(),
    install_requires=DEPENDENCIES
)
