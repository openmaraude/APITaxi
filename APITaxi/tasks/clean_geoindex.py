from ..extensions import celery, redis_store
from APITaxi_models.taxis import Taxi
import time
from flask import current_app

@celery.task
def clean_geoindex():
    keys_to_clean = []
    cursor = 0
    taxi_id = set()
    cursor = None
    while cursor != 0:
        if cursor == None:
            cursor = 0
        cursor, result = redis_store.scan(cursor, 'taxi:*')
        pipe = redis_store.pipeline()
        for key in result:
            pipe.hvals(key)
        values = pipe.execute()
        lower_bound = int(time.time()) - 60 * 60
        pipe = redis_store.pipeline()
        for (key, l) in zip(result, values):
            if any(map(lambda v: Taxi.parse_redis(v)['timestamp'] >= lower_bound, l)):
                continue
            pipe.zrem(current_app.config['REDIS_GEOINDEX'], key)
        pipe.execute()
#Maybe it'll more efficient to delete some of the taxis in the global map, but
#if we do it we'll lose the information of when this taxis was active for the
#last time, it will be great to log it in database.
