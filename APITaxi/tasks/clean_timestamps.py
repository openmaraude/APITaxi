#coding: utf-8
from ..extensions import celery, redis_store
from flask import current_app
from time import time
from ..models.taxis import TaxiRedis

@celery.task()
def clean_timestamps():
    max_time = time() - TaxiRedis._DISPONIBILITY_DURATION
    to_delete = redis_store.zrangebyscore(current_app.config['REDIS_TIMESTAMPS'],
        0, max_time)
    redis_store.zrem(current_app.config['REDIS_GEOINDEX'], to_delete)
    redis_store.zremrangebyscore(current_app.config['REDIS_TIMESTAMPS'],
        0, max_time)
