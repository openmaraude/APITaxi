#coding: utf-8
from ..extensions import celery, redis_store
from flask import current_app
from time import time
from ..models.taxis import TaxiRedis

@celery.task()
def clean_timestamps():
    redis_store.zremrangebyscore(current_app.config['REDIS_TIMESTAMPS'],
            0, time() - TaxiRedis._DISPONIBILITY_DURATION)
