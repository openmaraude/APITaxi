from setuptools import find_packages, setup
import os
import re


PACKAGE = 'APITaxi'

DEPENDENCIES = [
    'APITaxi_models',
    'Flask-Redis',
    'Flask-Cors',
    'psycopg2',
    'geopy',
    'Flask-Migrate',
    'bcrypt',
    'Geohash2',
    'redis',
    'email-validator',
    'marshmallow',
    'flask-influxdb',
    'apispec-webframeworks',
    # Celery 5 has been recently released, but celery-flower is not yet
    # compatible with the latest version.
    # We should upgrade to 5 when flower is ok.
    # To check if flower is compatible with celery 5, simply start it. Now
    # (2020/10/15) an error as startup from starting.
    'celery==4.4.7',
    'apispec[validation]',
    'pyshp',
    'shortuuid',
    'dataclasses',  # for Python3.6
    'sentry-sdk[flask]',
    'prettytable',
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
