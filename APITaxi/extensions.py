#coding: utf-8
from APITaxi_utils.redis_geo import GeoRedis
from flask.ext.redis import FlaskRedis
redis_store = FlaskRedis.from_custom_provider(GeoRedis)

from flask.ext.celery import Celery
celery = Celery()


from .index_zupc import IndexZUPC
index_zupc = IndexZUPC()

from APITaxi_utils.cache_user_datastore import CacheUserDatastore
user_datastore = CacheUserDatastore()
