from datetime import datetime, timedelta
import json as json_module
import requests
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

    def test_two_operators(self, app):
        """Make sure it is possible to fetch Hail related to a Taxi with two
        VehicleDescription."""
        hail = HailFactory(status='received_by_operator')
        VehicleDescriptionFactory(vehicle=hail.taxi.vehicle)

        with mock.patch.object(tasks.operators.current_app.logger, 'error') as mocked_logger:
            tasks.handle_hail_timeout(hail.id, hail.operateur.id, 'sent_to_operator', 'failure')
            assert mocked_logger.call_count == 0

    def test_hail_not_found(self, app):
        with mock.patch.object(tasks.operators.current_app.logger, 'error') as mocked_logger:
            tasks.handle_hail_timeout('1234', '5678', 'received', 'failure')
            assert mocked_logger.call_count == 1


class TestSendRequestOperator:
    def test_hail_not_found(self, app):
        with mock.patch.object(tasks.operators.current_app.logger, 'error') as mocked_logger:
            ret = tasks.send_request_operator('1234', None, None, None)
            assert mocked_logger.call_count == 1
            assert ret is False

    def test_hail_not_received(self, app):
        """Send request for an operator when hail status is different from "received"."""
        hail = HailFactory(status='finished')
        with mock.patch.object(tasks.operators.current_app.logger, 'error') as mocked_logger:
            ret = tasks.send_request_operator(hail.id, None, None, None)
            assert mocked_logger.call_count == 1
            assert ret is False

    def test_task_called_too_late(self, app):
        """When user makes hail request, we should immediately forward it to
        the operator. If the worker is not running because of production issue,
        we should not attempt to deliver the hail to the operator and instead
        mark the hail as failure.
        """
        hail = HailFactory(
            status='received',
            added_at=datetime.now() - timedelta(seconds=45)
        )
        hail_id = hail.id
        with mock.patch.object(tasks.operators.current_app.logger, 'error') as mocked_logger:
            ret = tasks.send_request_operator(hail.id, None, None, None)
            assert mocked_logger.call_count == 1
            assert ret is False
            assert Hail.query.get(hail_id).status == 'failure'

    def test_ok(self, app):
        """Hail is successfully sent to the operator API, which returns the
        taxi phone number.
        """
        hail = HailFactory(status='received')
        # Create extra VehicleDescription for the vehicle to make sure the view
        # can handle this case.
        VehicleDescriptionFactory(vehicle=hail.taxi.vehicle)

        operator_endpoint = 'http://127.0.0.1:9876'
        operator_header_name = 'My-Header'
        operator_header_value = 'My-Value'
        taxi_phone_number = '+1234'

        def requests_post(url, json=None, headers=None):
            assert url == operator_endpoint
            assert headers.get(operator_header_name) == operator_header_value
            # Location is not available because taxi hasn't accepted the hail request yet.
            assert json['data'][0]['taxi']['position']['lon'] is None
            assert json['data'][0]['taxi']['position']['lat'] is None

            content = {
                'data': [{
                    'taxi_phone_number': taxi_phone_number
                }]
            }
            resp = requests.Response()
            resp.status_code = 200
            resp._content = json_module.dumps(content).encode('utf8')
            return resp

        with mock.patch(
            'requests.post', requests_post
        ), mock.patch.object(
            tasks.operators.handle_hail_timeout, 'apply_async'
        ) as mocked_handle_hail_timeout, mock.patch(
            'flask.current_app.logger.info'
        ) as mocked_logger:
            ret = tasks.send_request_operator(
                hail.id, operator_endpoint,
                operator_header_name, operator_header_value
            )
            assert ret is True
            assert mocked_handle_hail_timeout.call_count == 1
            assert mocked_logger.call_count == 1

        assert hail.status == 'received_by_operator'
        assert hail.taxi_phone_number == taxi_phone_number
        # Make sure hail request is logged.
        assert len(app.redis.zrange('hail:%s' % hail.id, 0, -1)) == 1

    def test_operator_api_unavailable(self, app):
        """Failure to connect to operator API makes the hail as failure, and
        logs the error."""
        hail = HailFactory(status='received')
        hail_id = hail.id

        def requests_post(*args, **kwargs):
            raise requests.exceptions.RequestException('failure')

        with mock.patch(
            'requests.post', requests_post
        ), mock.patch(
            'flask.current_app.logger.error'
        ) as mocked_logger:
            ret = tasks.send_request_operator(hail.id, 'http://whatever', None, None)
            assert ret is False
            assert mocked_logger.call_count == 1

        hail = Hail.query.get(hail_id)
        assert hail.status == 'failure'
        # Check that failure is logged
        assert len(app.redis.zrange('hail:%s' % hail_id, 0, -1)) == 1

    def test_operator_api_response_not_json(self, app):
        """If operator API doesn't return JSON, mark hail as error."""
        hail = HailFactory(status='received')
        hail_id = hail.id

        def requests_post(*args, **kwargs):
            resp = requests.Response()
            resp.status_code = 200
            resp._content = b'{;[not json'
            return resp

        with mock.patch(
            'requests.post', requests_post
        ), mock.patch(
            'flask.current_app.logger.error'
        ) as mocked_logger:
            ret = tasks.send_request_operator(hail.id, 'http://whatever', None, None)
            assert ret is False
            assert mocked_logger.call_count == 1

        hail = Hail.query.get(hail_id)
        assert hail.status == 'failure'
        # Check that failure is logged
        assert len(app.redis.zrange('hail:%s' % hail_id, 0, -1)) == 1

    def test_operator_api_response_not_2xx(self, app):
        """Operator API didn't respond with HTTP/2xx."""
        hail = HailFactory(status='received')
        hail_id = hail.id

        def requests_post(*args, **kwargs):
            resp = requests.Response()
            resp.status_code = 404
            resp._content = b''
            return resp

        with mock.patch(
            'requests.post', requests_post
        ), mock.patch(
            'flask.current_app.logger.error'
        ) as mocked_logger:
            ret = tasks.send_request_operator(hail.id, 'http://whatever', None, None)
            assert ret is False
            assert mocked_logger.call_count == 1

        hail = Hail.query.get(hail_id)
        assert hail.status == 'failure'
        # Check that failure is logged
        assert len(app.redis.zrange('hail:%s' % hail_id, 0, -1)) == 1
