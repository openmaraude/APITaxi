import time

from celery import shared_task
from flask import current_app


@shared_task(name='clean_geoindex_timestamps')
def clean_geoindex_timestamps():
    """Geotaxi stores locations in several Redis keys:

    - in the sorted sets "geoindex" and "timestamps_id", members are "taxi_id"
    - in the sorted sets "geoindex_2" and "timestamps", members are "taxi_id:operator"

    A spatial index is a sorted set with the geohash as the score, so zremrangebyscore isn't an option.
    Instead we store location update time as a score in a separare "timestamps" sorted set,
    and every two minutes, we delete scores inferior to the threshold timestamp, and then we delete
    geoindex members not found in "timestamps" anymore.

    This task removes data older than two minutes.

    The taxi hash set (taxi:<taxi_id>) is not affected.
    """
    max_time = int(time.time() - 120)
    current_app.logger.info('Run task clean_geoindex_timestamps for data older than %s', max_time)

    current_app.redis.zremrangebyscore('timestamps', 0, max_time)
    # Remove members of geoindex_2 not found in timestamps (just removed)
    current_app.redis.zinterstore('geoindex_2', {
        'timestamps': 0,
        'geoindex_2': 1
    })

    current_app.redis.zremrangebyscore('timestamps_id', 0, max_time)
    # Remove members of geoindex not found in timestamps_id (just removed)
    current_app.redis.zinterstore('geoindex', {
        'timestamps_id': 0,
        'geoindex': 1
    })
