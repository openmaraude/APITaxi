#coding: utf-8
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.pool import QueuePool as BaseQueuePool

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
    'zupc': make_region('zupc'),
    'users': make_region('users')
}

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

