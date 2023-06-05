from setuptools import find_packages, setup
import os
import re


PACKAGE = 'APITaxi'

DEPENDENCIES = [
    'alembic>=1.11.1,<1.12',
    'aniso8601',
    'apispec[validation,marshmallow]>=6.3.0,<6.4',
    'apispec-webframeworks',
    'bcrypt',
    'celery',
    'email-validator',
    'Flask>=2.3.2,<2.4',
    'Flask-Cors',
    'Flask-HTTPAuth>=4.8,<4.9',
    'Flask-Login>=0.6.2,<0.7',
    'Flask-Migrate>=4.0.4,<5',
    'Flask-Principal',
    'Flask-Redis',
    'Flask-Security-Too[common]>=5.2,<5.3',
    'Flask-SQLAlchemy>=3.0,<4',
    'GeoAlchemy2>=0.13.3,<0.14',
    'Geohash2',
    'geopy',
    'parse',
    'prettytable',
    'psycopg2>=2.9.6,<3',
    'pyshp',
    'pytz>=2023.3',
    'redis>=4.5.5,<5',
    'hiredis>=2.2.3,<2.3',
    'sentry-sdk[flask]',
    'Shapely>=2.0.1,<2.1',
    'shortuuid',
    'SQLAlchemy>=2.0,<2.1',
    'SQLAlchemy-Defaults',
    'SQLAlchemy-Utils',
    'tzdata',
    'Werkzeug>=2.3,<2.4',
    'watchdog[watchmedo]>=3.0.0',
]

TEST_DEPENDENCIES = [
    'pytest',
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
