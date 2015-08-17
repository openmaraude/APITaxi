#coding: utf-8
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy(session_options={"autoflush":False})
from .utils.redis_geo import GeoRedis
from flask.ext.redis import FlaskRedis
redis_store = FlaskRedis.from_custom_provider(GeoRedis)

from dogpile.cache import make_region
region_taxi = make_region('taxis')
region_hails = make_region('hails')
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
