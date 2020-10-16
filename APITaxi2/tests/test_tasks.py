import time
from unittest import mock

from APITaxi_models2 import Hail, VehicleDescription
from APITaxi_models2.unittest.factories import HailFactory, VehicleDescriptionFactory

from .. import tasks


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


class TestHandleHailTimeout:
    def test_timeout(self, app):
        """Hail reaches timeout. Status is initially sent_to_operator, and it
        still has the same status when timeout function is called. New taxi
        status is 'off'."""
        hail = HailFactory(status='sent_to_operator')
        hail_id = hail.id

        # Hail status timeout: it is still sent_to_operator
        with mock.patch.object(tasks.operators.current_app.logger, 'warning') as mocked_logger:
            tasks.handle_hail_timeout(hail.id, hail.operateur.id, 'sent_to_operator', 'failure', 'off')
            assert mocked_logger.call_count == 1

        # Since handle_hail_timeout commits the session, we have to fetch Hail
        # back to read its properties.
        hail = Hail.query.get(hail_id)
        assert hail.status == 'failure'

        vehicle_description = VehicleDescription.query.one()
        assert vehicle_description.status == 'off'

    def test_no_timeout(self, app):
        """Hail doesn't reach timeout. Status is initially
        received_by_operator, and it is sent_to_operator when timeout function
        is called."""
        hail = HailFactory(status='sent_to_operator')
        VehicleDescriptionFactory(vehicle=hail.taxi.vehicle)

        hail.status = 'received_by_operator'
        with mock.patch.object(tasks.operators.current_app.logger, 'warning') as mocked_logger:
            tasks.handle_hail_timeout(hail.id, hail.operateur.id, 'sent_to_operator', 'failure', None)
            assert mocked_logger.call_count == 0

        # No need to fetch back hail since session has not been committed.
        assert hail.status == 'received_by_operator'
