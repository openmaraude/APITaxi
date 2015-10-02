#coding: utf-8
from flask_sqlalchemy import SQLAlchemy as BaseSQLAlchemy
from sqlalchemy.pool import QueuePool as BaseQueuePool


class SQLAlchemy(BaseSQLAlchemy):
    def apply_driver_hacks(self, app, info, options):
        BaseSQLAlchemy.apply_driver_hacks(self, app, info, options)
        class QueuePool(BaseQueuePool):
            def  __init__(self, creator, pool_size=5, max_overflow=10, timeout=30, **kw):
                kw['use_threadlocal'] = True
                BaseQueuePool.__init__(self, creator, pool_size, max_overflow, timeout, **kw)
        options.setdefault('poolclass', QueuePool)
db = SQLAlchemy(session_options={"autoflush":False})
from .utils.redis_geo import GeoRedis
from flask.ext.redis import FlaskRedis
redis_store = FlaskRedis.from_custom_provider(GeoRedis)

from flask.ext.celery import Celery
celery = Celery()

from dogpile.cache import make_region
regions = {
    'taxis': make_region('taxis'),
    'hails': make_region('hails'),
    'zupc': make_region('zupc')
}
def user_key_generator(namespace, fn, **kw):
    def generate_key(*args, **kwargs):
        return fn.__name__ +\
             "_".join(str(s) for s in args) +\
             "_".join(k+"_"+str(v) for k,v in kwargs.iteritems())
    return generate_key
region_users = make_region('users', function_key_generator=user_key_generator)

from flask.ext.uploads import (UploadSet, configure_uploads,
            DOCUMENTS, DATA, ARCHIVES, IMAGES)
documents = UploadSet('documents', DOCUMENTS + DATA + ARCHIVES)
images = UploadSet('images', IMAGES)


from .index_zupc import IndexZUPC
index_zupc = IndexZUPC()

from .utils.cache_user_datastore import CacheUserDatastore
from .models import security
user_datastore = CacheUserDatastore(db, security.User,
                            security.Role)
import shortuuid
suid = shortuuid.ShortUUID()

def get_short_uuid():
    return suid.uuid()[:7]

