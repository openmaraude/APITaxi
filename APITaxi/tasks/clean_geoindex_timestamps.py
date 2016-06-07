from ..extensions import celery, redis_store
from APITaxi_models.taxis import TaxiRedis
import time
from flask import current_app

@celery.task
def clean_geoindex_timestamps():
    max_time = time() - TaxiRedis._DISPONIBILITY_DURATION
    redis_store.zremrangebyscore(current_app.config['REDIS_TIMESTAMPS'],
        0, max_time)
    redis_store.zinterstore(current_app.config['REDIS_GEOINDEX'], 
                            {current_app.config['REDIS_GEOINDEX']:1,
                             current_app.config['REDIS_TIMESTAMPS']:0})
