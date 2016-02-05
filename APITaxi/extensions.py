#coding: utf-8

from APITaxi_utils.redis_geo import GeoRedis
from flask.ext.redis import FlaskRedis
redis_store = FlaskRedis.from_custom_provider(GeoRedis)

from flask.ext.celery import Celery
celery = Celery()

regions = {
    'taxis': None,
    'hails': None,
    'zupc': None,
    'taxis_zupc': None,
    'taxis_cache_sql': None,
    'users': None
}

from flask.ext.uploads import (UploadSet, configure_uploads,
            DOCUMENTS, DATA, ARCHIVES, IMAGES)
documents = UploadSet('documents', DOCUMENTS + DATA + ARCHIVES)
images = UploadSet('images', IMAGES)


from .index_zupc import IndexZUPC
index_zupc = IndexZUPC()

from APITaxi_utils.cache_user_datastore import CacheUserDatastore
user_datastore = CacheUserDatastore()
