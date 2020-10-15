import time

from flask import current_app

from . import celery


@celery.task(name='clean_geoindex_timestamps')
def clean_geoindex_timestamps():
    """Geotaxi stores locations:

    - in the ZSETs "geoindex" and "timestamps_id", keys are "taxi_id"
    - in the ZSETs "geoindex_2" and "timestamps", keys are "taxi_id:operator"

    This task remove expired data.
    """
    max_time = time.time() - 120

    current_app.redis.zremrangebyscore('timestamps', 0, max_time)
    current_app.redis.zinterstore('geoindex_2', {
        'timestamps': 0,
        'geoindex_2': 1
    })

    current_app.redis.zremrangebyscore('timestamps_id', 0, max_time)
    current_app.redis.zinterstore('geoindex', {
        'timestamps_id': 0,
        'geoindex': 1
    })
