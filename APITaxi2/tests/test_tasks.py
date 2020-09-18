import time

from APITaxi2 import tasks


class TestCleanGeoindexTimestamps:
    def test_expired(self, app):
        now = time.time()
        expired = now - 300

        # Store fresh locations
        app.redis.zadd('timestamps_id', {'FRESH_TAXI_ID': now})
        app.redis.geoadd('geoindex', 2.22, 48.88, 'FRESH_TAXI_ID')
        app.redis.zadd('timestamps', {'FRESH_TAXI_ID:OPERATOR': now})
        app.redis.geoadd('geoindex_2', 2.22, 48.88, 'FRESH_TAXI_ID:OPERATOR')

        # Store expired locations
        app.redis.zadd('timestamps_id', {'EXPIRED_TAXI_ID': expired})
        app.redis.geoadd('geoindex', 2.22, 48.88, 'EXPIRED_TAXI_ID')
        app.redis.zadd('timestamps', {'EXPIRED_TAXI_ID:OPERATOR': expired})
        app.redis.geoadd('geoindex_2', 2.22, 48.88, 'EXPIRED_TAXI_ID:OPERATOR')

        tasks.clean_geoindex_timestamps()

        # Expired locations have been removed, fresh locations are still there
        assert len(app.redis.zrange('timestamps_id', 0, -1)) == 1
        assert len(app.redis.zrange('geoindex', 0, -1)) == 1
        assert len(app.redis.zrange('timestamps', 0, -1)) == 1
        assert len(app.redis.zrange('geoindex_2', 0, -1)) == 1
