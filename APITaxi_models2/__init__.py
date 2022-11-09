"""APITaxi_models version 1 is a pretty bad library but it is also almost
impossible to update it because too many components depend in it.

APITaxi_models2 had the following features:

    * NOT compatible with APITaxi_models
    * No code in magic methods (__init__()) which makes unittests near
      impossible
    * Better fieldnames convention
    * Relationship defined everywhere
    * Exports library functions that must be called explicitely, instead of
      magically

The goal is to migrate to APITaxi_models2 one API endpoint at a time, and to
completely get rid of APITaxi_models in the future.

The goal is not to reflect the underlying database. Upgrading schema will come
when the migration is completely done.
"""

__author__ = 'Julien Castets'
__contact__ = 'julien.castets@beta.gouv.fr'
__homepage__ = 'https://github.com/openmaraude/APITaxi_models'
__version__ = '0.1.0'
__doc__ = 'Models used by APITaxi'


from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .ads import ADS  # noqa
from .customer import Customer  # noqa
from .departement import Departement  # noqa
from .driver import Driver  # noqa
from .hail import Hail  # noqa
from .station import Station  # noqa
from .stats import *  # noqa
from .taxi import Taxi  # noqa
from .user import Role, RolesUsers, User  # noqa
from .vehicle import Vehicle, VehicleDescription  # noqa
from .zupc import Town, ZUPC  # noqa
