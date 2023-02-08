from setuptools import find_packages, setup
import os
import re


PACKAGE = 'APITaxi'

DEPENDENCIES = [
    'aniso8601',
    'apispec[validation,marshmallow]>=6.0',
    'apispec-webframeworks',
    'openapi-spec-validator',
    'bcrypt',
    'celery',
    'email-validator',
    'Flask<2.2',
    'Flask-Cors',
    'Flask-Login==0.6.1',  # 0.6.2 breaks because of Flask<2.2 ?
    'Flask-Migrate',
    'Flask-Principal',
    'Flask-Redis',
    'Flask-Security',
    'Flask-SQLAlchemy<3.0',  # requires Flask>=2.2
    'GeoAlchemy2',
    'Geohash2',
    'geopy',
    'parse',
    'prettytable',
    'psycopg2',
    'pyshp',
    'redis',
    'hiredis',
    'sentry-sdk[flask]',
    'Shapely',
    'shortuuid',
    'SQLAlchemy<2.0',
    'SQLAlchemy-Defaults',
    'SQLAlchemy-Utils',
    'Werkzeug<2.2',
]

TEST_DEPENDENCIES = [
    'pytest',
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
