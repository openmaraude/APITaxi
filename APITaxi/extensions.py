#coding: utf-8
from flask_redis import FlaskRedis
redis_store = FlaskRedis()
redis_store_saved = FlaskRedis(config_prefix='REDIS_SAVED')

from flask_celery import Celery
celery = Celery()

from APITaxi_utils.cache_user_datastore import CacheUserDatastore
user_datastore = CacheUserDatastore()
