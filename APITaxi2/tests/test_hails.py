from datetime import datetime, timedelta
import json
import time
from unittest import mock
import uuid

import requests
import sqlalchemy

from APITaxi2 import tasks, utils
from APITaxi_models2 import Hail, Taxi, Vehicle, VehicleDescription
from APITaxi_models2.unittest.factories import (
    CustomerFactory,
    HailFactory,
    TaxiFactory,
    VehicleFactory,
    VehicleDescriptionFactory,
)


class TestGetHailDetails:
    def test_invalid(self, anonymous, operateur, moteur):
        # Login required
        resp = anonymous.client.get('/hails/xxx')
        assert resp.status_code == 401

        # Hail does not exist
        resp = operateur.client.get('/hails/xxxx')
        assert resp.status_code == 404

        # User making the query is not the hail's moteur or operateur.
        hail = HailFactory()
        resp = operateur.client.get('/hails/%s' % hail.id)
        assert resp.status_code == 403

    def test_ok(self, app, admin, operateur, moteur, QueriesTracker):
        hail = HailFactory(operateur=operateur.user, added_by=moteur.user)
        with QueriesTracker() as qtracker:
            resp = admin.client.get('/hails/%s' % hail.id)
        assert resp.status_code == 200
        assert resp.json['data'][0]['operateur'] == operateur.user.email
        # SELECT permissions, SELECT hail
        assert qtracker.count == 2

        # The user is the moteur
        resp = moteur.client.get('/hails/%s' % hail.id)
        assert resp.status_code == 200
        assert resp.json['data'][0]['operateur'] == 'chauffeur professionnel'

        # The user is the operateur
        resp = operateur.client.get('/hails/%s' % hail.id)
        assert resp.status_code == 200
        assert resp.json['data'][0]['operateur'] == operateur.user.email

        # From hail creation until it's end, it is possible to get the taxi
        # location.
        for status in (
            'received',
            'sent_to_operator',
            'received_by_operator',
            'received_by_taxi',
            'accepted_by_taxi',
            'accepted_by_customer',
            'customer_on_board',
        ):
            hail = HailFactory(
                status=status, added_by=moteur.user, operateur=operateur.user,
                taxi__vehicle__descriptions__color="blue",
            )
            app.redis.hset(
                'taxi:%s' % hail.taxi.id,
                hail.operateur.email,
                '1589567716 48.84 2.35 free phone 2'
            )
            resp = moteur.client.get('/hails/%s' % hail.id)
            assert resp.status_code == 200
            assert resp.json['data'][0]['operateur'] == 'chauffeur professionnel'
            assert resp.json['data'][0]['taxi']['crowfly_distance']
            assert resp.json['data'][0]['taxi']['last_update']
            assert resp.json['data'][0]['taxi']['position']['lon']
            assert resp.json['data'][0]['taxi']['position']['lat']

            # For backward compatibility, taxi_id is not returned from GET
            # /hails/:id, but the field is required to create a taxi with POST
            # /hails/:id
            assert 'taxi_id' not in resp.json['data'][0]

            # Vehicle details are only accessible when the hail is accepted
            accepted = status in ('accepted_by_taxi', 'accepted_by_customer', 'customer_on_board')
            assert bool(resp.json['data'][0]['taxi']['vehicle']['licence_plate']) == accepted
            assert bool(resp.json['data'][0]['taxi']['vehicle']['color']) == accepted
            assert bool(resp.json['data'][0]['taxi']['driver']['last_name']) == accepted

        # Position exists in redis and hail is finished: location is not returned
        hail = HailFactory(status='finished', added_by=moteur.user, operateur=operateur.user)
        app.redis.hset(
            'taxi:%s' % hail.taxi.id,
            hail.added_by.email,
            '1589567716 48.84 2.35 free phone 2'
        )
        resp = moteur.client.get('/hails/%s' % hail.id)
        assert resp.status_code == 200
        assert resp.json['data'][0]['operateur'] == 'chauffeur professionnel'
        assert not resp.json['data'][0]['taxi']['crowfly_distance']
        assert not resp.json['data'][0]['taxi']['last_update']
        assert not resp.json['data'][0]['taxi']['position']['lon']
        assert not resp.json['data'][0]['taxi']['position']['lat']
        assert not resp.json['data'][0]['taxi']['vehicle']['licence_plate']
        assert not resp.json['data'][0]['taxi']['vehicle']['color']
        assert not resp.json['data'][0]['taxi']['driver']['last_name']

    def test_ok_two_operators(self, app, operateur):
        """Get hail details of a taxi with two VehicleDescription entries."""
        hail = HailFactory(operateur=operateur.user)
        VehicleDescriptionFactory(vehicle=hail.taxi.vehicle)

        resp = operateur.client.get('/hails/%s' % hail.id)
        assert resp.status_code == 200
        assert resp.json['data'][0]['operateur'] == operateur.user.email

    def test_old_hail(self, admin, moteur, operateur):
        hail = HailFactory(
            operateur=operateur.user,
            added_by=moteur.user,
            added_at=datetime.now() - timedelta(60)
        )

        resp = moteur.client.get(f'/hails/{hail.id}')
        assert resp.status_code == 404

        resp = operateur.client.get(f'/hails/{hail.id}')
        assert resp.status_code == 404

        resp = admin.client.get(f'/hails/{hail.id}')
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1


class TestEditHail:
    def test_invalid(self, anonymous, operateur, moteur):
        # Login required
        resp = anonymous.client.put('/hails/xxx', json={})
        assert resp.status_code == 401

        # Hail does not exist
        resp = operateur.client.put('/hails/xxxx', json={})
        assert resp.status_code == 404

        # User making the query is not the hail's moteur or operateur.
        hail = HailFactory()
        resp = operateur.client.put('/hails/%s' % hail.id, json={})
        assert resp.status_code == 403

        # Change to accepted_by_taxi but no phone number provided
        hail = HailFactory(operateur=operateur.user, status='received')
        resp = operateur.client.put('/hails/%s' % hail.id, json={'data': [{
            'status': 'accepted_by_taxi',
        }]})
        assert resp.status_code == 400
        assert len(resp.json['errors']['data']['0']['status']) == 1

    def test_ok(self, app, operateur):
        hail = HailFactory(operateur=operateur.user, status='received_by_taxi')

        # On creation, VehicleDescription linked to hail.taxi is free
        assert VehicleDescription.query.join(Vehicle).join(Taxi).filter(
            Taxi.id == hail.taxi_id
        ).one().status == 'free'

        with mock.patch.object(tasks.handle_hail_timeout, 'apply_async') as mocked_handle_hail_timeout:
            resp = operateur.client.put('/hails/%s' % hail.id, json={'data': [{
                'status': 'accepted_by_taxi',
                'taxi_phone_number': '+33612345678'
            }]})
            assert mocked_handle_hail_timeout.call_count == 1

        assert resp.status_code == 200
        assert resp.json['data'][0]['id'] == hail.id
        assert resp.json['data'][0]['status'] == 'accepted_by_taxi'
        assert resp.json['data'][0]['taxi_phone_number'] == '0600000000'  # Obsfucated

        # Make sure request is logged
        assert len(app.redis.zrange('hail:%s' % hail.id, 0, -1)) == 1

        # Check transition log
        hail = Hail.query.filter(Hail.id == hail.id).one()
        assert hail.transition_log[-1]['from_status'] == 'received_by_taxi'
        assert hail.transition_log[-1]['to_status'] == 'accepted_by_taxi'
        assert hail.transition_log[-1]['user'] == operateur.user.id

    def test_ok_change_taxi_status(self, app, operateur, moteur):
        """Same than test_ok, but when status changes to accepted_by_customer, taxi's status changes to "oncoming".
        """
        hail = HailFactory(
            added_by=moteur.user,
            operateur=operateur.user,
            status='accepted_by_taxi',
            taxi_phone_number='+33612345678',
        )

        # On creation, VehicleDescription linked to hail.taxi is free
        assert VehicleDescription.query.join(Vehicle).join(Taxi).filter(
            Taxi.id == hail.taxi_id
        ).one().status == 'free'

        with mock.patch.object(tasks.handle_hail_timeout, 'apply_async') as mocked_handle_hail_timeout:
            resp = moteur.client.put('/hails/%s' % hail.id, json={'data': [{
                'status': 'accepted_by_customer',
            }]})
            assert mocked_handle_hail_timeout.call_count == 1

        assert resp.status_code == 200
        assert resp.json['data'][0]['id'] == hail.id
        assert resp.json['data'][0]['status'] == 'accepted_by_customer'
        assert resp.json['data'][0]['taxi_phone_number'] == '+33612345678'  # Not obsfucated

        # When the hail's status changes to "accepted_by_taxi", taxi's status
        # becomes "incoming".
        assert VehicleDescription.query.join(Vehicle).join(Taxi).filter(
            Taxi.id == hail.taxi_id
        ).one().status == 'oncoming'

        # Make sure request is logged
        assert len(app.redis.zrange('hail:%s' % hail.id, 0, -1)) == 1

        # Check transition log
        hail = Hail.query.filter(Hail.id == hail.id).one()
        assert hail.transition_log[-1]['from_status'] == 'accepted_by_taxi'
        assert hail.transition_log[-1]['to_status'] == 'accepted_by_customer'
        assert hail.transition_log[-1]['user'] == moteur.user.id

    def test_ko_change_operateur_param_by_moteur(self, moteur, operateur):
        """Moteur attempts to change a field that can only be updated by an
        operateur."""
        hail = HailFactory(operateur=operateur.user, added_by=moteur.user, status='accepted_by_taxi')

        resp = moteur.client.put('/hails/%s' % hail.id, json={'data': [{
            'incident_taxi_reason': 'no_show'
        }]})
        assert resp.status_code == 400
        assert len(resp.json['errors']['data']['0']['incident_taxi_reason']) == 1

    def test_ok_ban_customer(self, moteur, operateur):
        # Create unbanned customer
        customer = CustomerFactory(added_by=moteur.user, ban_begin=None, ban_end=None)
        hail = HailFactory(
            customer=customer,
            added_by=moteur.user,
            operateur=operateur.user,
            status='accepted_by_taxi',
        )
        # Ban
        resp = operateur.client.put('/hails/%s' % hail.id, json={'data': [{
            'incident_taxi_reason': 'no_show',
            'reporting_customer': True
        }]})
        assert resp.status_code == 200
        assert customer.ban_begin
        assert customer.ban_end

    def test_ok_ban_customer_again(self, moteur, operateur):
        # Create banned customer
        customer = CustomerFactory(
            added_by=moteur.user,
            ban_begin=sqlalchemy.func.NOW(),
            ban_end=sqlalchemy.func.NOW() + timedelta(hours=+24),
        )
        original_ban_begin = customer.ban_begin
        original_ban_end = customer.ban_end
        # Ban again
        hail = HailFactory(
            customer=customer,
            added_by=moteur.user,
            operateur=operateur.user,
            status='accepted_by_taxi',
        )
        resp = operateur.client.put('/hails/%s' % hail.id, json={'data': [{
            'reporting_customer': True,
            'incident_taxi_reason': 'no_show',
        }]})
        assert resp.status_code == 200
        assert customer.ban_begin == original_ban_begin
        assert customer.ban_end > original_ban_end

    def test_ok_unban_customer(self, moteur, operateur):
        # Create banned customer
        customer = CustomerFactory(
            added_by=moteur.user,
            ban_begin=sqlalchemy.func.NOW(),
            ban_end=sqlalchemy.func.NOW() + timedelta(hours=+24),
        )
        assert customer.ban_begin
        assert customer.ban_end
        # Unban
        hail = HailFactory(
            customer=customer,
            added_by=moteur.user,
            operateur=operateur.user,
            status='accepted_by_taxi',
            reporting_customer=True,
        )
        resp = operateur.client.put('/hails/%s' % hail.id, json={'data': [{
            'reporting_customer': False
        }]})
        assert resp.status_code == 200
        assert not customer.ban_begin
        assert not customer.ban_end

    def test_ko_change_moteur_param_by_operateur(self, moteur, operateur):
        """Operateur attempts to change a field that can only be updated by an
        moteur."""
        hail = HailFactory(operateur=operateur.user, added_by=moteur.user, status='accepted_by_taxi')

        resp = operateur.client.put('/hails/%s' % hail.id, json={'data': [{
            'customer_lon': 3.23
        }]})
        assert resp.status_code == 400
        assert len(resp.json['errors']['data']['0']['customer_lon']) == 1

    def test_ok_change_moteur_param(self, moteur):
        hail = HailFactory(added_by=moteur.user, status='accepted_by_customer')

        resp = moteur.client.put('/hails/%s' % hail.id, json={'data': [{
            'customer_lon': 3.23
        }]})
        assert resp.status_code == 200
        assert resp.json['data'][0]['customer_lon'] == 3.23
        assert hail.customer_lon == 3.23

    def test_async_timeouts(self, app, operateur, moteur):
        """Check hail status changes which generate an asynchronous call to the
        task handle_hail_timeout.

        For example, when the hail status is "received_by_taxi", taxi has 30
        seconds to accept or refuse the hail, otherwise the status
        automatically becomes "timeout_taxi".
        """
        hail = HailFactory(added_by=moteur.user, operateur=operateur.user)

        # When hail is received by operator, taxi has 30 seconds to accept or
        # refuse the request.
        hail.status = 'received_by_operator'
        with mock.patch.object(tasks.handle_hail_timeout, 'apply_async') as mocked_handle_hail_timeout:
            operateur.client.put('/hails/%s' % hail.id, json={'data': [{
                'status': 'received_by_taxi'
            }]})
            mocked_handle_hail_timeout.assert_called_with(
                args=(hail.id, operateur.user.id),
                kwargs={
                    'initial_hail_status': 'received_by_taxi',
                    'new_hail_status': 'timeout_taxi',
                    'new_taxi_status': 'off'
                },
                countdown=30
            )

        # When taxi accepts the request, customer has 60 seconds to accept or
        # refuse the request.
        hail.status = 'received_by_taxi'
        with mock.patch.object(tasks.handle_hail_timeout, 'apply_async') as mocked_handle_hail_timeout:
            operateur.client.put('/hails/%s' % hail.id, json={'data': [{
                'status': 'accepted_by_taxi',
                'taxi_phone_number': '+3362342'
            }]})
            mocked_handle_hail_timeout.assert_called_with(
                args=(hail.id, operateur.user.id),
                kwargs={
                    'initial_hail_status': 'accepted_by_taxi',
                    'new_hail_status': 'timeout_customer',
                    'new_taxi_status': 'free'
                },
                countdown=30
            )

        # When customer accepts the request, taxi has 30 minutes to pickup the
        # client.
        hail.status = 'accepted_by_taxi'
        with mock.patch.object(tasks.handle_hail_timeout, 'apply_async') as mocked_handle_hail_timeout:
            moteur.client.put('/hails/%s' % hail.id, json={'data': [{
                'status': 'accepted_by_customer'
            }]})
            mocked_handle_hail_timeout.assert_called_with(
                args=(hail.id, operateur.user.id),
                kwargs={
                    'initial_hail_status': 'accepted_by_customer',
                    'new_hail_status': 'timeout_accepted_by_customer',
                    'new_taxi_status': 'occupied'
                },
                countdown=60 * 30
            )

        # When customer is on board for more than 2 hours, timeout is raised.
        hail.status = 'accepted_by_customer'
        with mock.patch.object(tasks.handle_hail_timeout, 'apply_async') as mocked_handle_hail_timeout:
            operateur.client.put('/hails/%s' % hail.id, json={'data': [{
                'status': 'customer_on_board'
            }]})
            mocked_handle_hail_timeout.assert_called_with(
                args=(hail.id, operateur.user.id),
                kwargs={
                    'initial_hail_status': 'customer_on_board',
                    'new_hail_status': 'timeout_taxi',
                    'new_taxi_status': 'off'
                },
                countdown=60 * 60 * 2
            )

    def test_ok_skip_received_by_operator(self, operateur):
        """What happens if the operator declares the hail was received by the taxi
        even before we had time to set the hail as received by the operator.
        """
        hail = HailFactory(status='received', operateur=operateur.user)

        resp = operateur.client.put(f'/hails/{hail.id}', json={'data': [{
            'status': 'received_by_taxi'
        }]})
        assert resp.status_code == 400, resp.json
        assert len(resp.json['errors']['data']['0']['status']) == 1

    def test_update_customer_phone_number(self, moteur):
        """Customer shouldn't be allowed to change the phone number once hailing"""
        hail = HailFactory(
            added_by=moteur.user,
            status='accepted_by_taxi',
            customer_phone_number='+33607080910',
        )

        with mock.patch.object(tasks.handle_hail_timeout, 'apply_async'):
            resp = moteur.client.put(f'/hails/{hail.id}', json={'data': [{
                'status': 'accepted_by_customer',
                'customer_phone_number': '0600000000',
            }]})
        # Don't fail though
        assert resp.status_code == 200, resp.json
        assert hail.status == 'accepted_by_customer'
        assert hail.customer_phone_number == '+33607080910'

    def test_update_incident_taxi_reason(self, operateur):
        """Incident reason can be set after the fact."""
        hail = HailFactory(
            operateur=operateur.user,
            status='incident_taxi',
        )

        resp = operateur.client.put(f'/hails/{hail.id}', json={'data': [{
            'incident_taxi_reason': 'traffic',
        }]})
        assert resp.status_code == 200, resp.json
        assert hail.incident_taxi_reason == 'traffic'

    def test_update_incident_customer_reason(self, moteur):
        """Incident reason can be set after the fact."""
        hail = HailFactory(
            added_by=moteur.user,
            status='incident_customer',
            customer_phone_number='+33607080910',
        )

        resp = moteur.client.put(f'/hails/{hail.id}', json={'data': [{
            'incident_customer_reason': 'no_show',
        }]})
        assert resp.status_code == 200, resp.json
        assert hail.incident_customer_reason == 'no_show'


class TestGetHailList:
    def test_invalid(self, anonymous, moteur):
        # Login required
        resp = anonymous.client.get('/hails/')
        assert resp.status_code == 401

        # Non existing parameter
        resp = moteur.client.get('/hails/?invalid_field=xxx')
        assert resp.status_code == 400
        assert 'invalid_field' in resp.json['errors']

        # Invalid status
        resp = moteur.client.get('/hails/?status=xxx')
        assert resp.status_code == 400
        assert 'status' in resp.json['errors']

    def test_ok(self, admin, moteur, operateur, QueriesTracker):
        hail1 = HailFactory(operateur=operateur.user, status='received')
        HailFactory(operateur=operateur.user, status='finished')
        HailFactory(added_by=moteur.user, status='finished')

        # Admin get all hails
        with QueriesTracker() as qtracker:
            resp = admin.client.get('/hails/')
            # SELECT permissions, SELECT hails. Depending on version, COUNT(*) for
            # pagination.
            assert qtracker.count <= 3

        assert resp.status_code == 200
        assert len(resp.json['data']) == 3

        # Operateur gets only its hails
        resp = operateur.client.get('/hails/')
        assert resp.status_code == 200
        assert len(resp.json['data']) == 2
        assert resp.json['data'][0]['operateur'] == operateur.user.email
        assert resp.json['data'][1]['operateur'] == operateur.user.email

        # Moteur gets only its hails
        resp = moteur.client.get('/hails/')
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['operateur'] == 'chauffeur professionnel'
        assert resp.json['data'][0]['added_by'] == moteur.user.email

        # Pagination information is returned
        resp = admin.client.get('/hails/')
        assert resp.status_code == 200
        assert resp.json['meta'] == {
            'next_page': None,
            'prev_page': None,
            'per_page': 30,
            'pages': 1,
            'total': 3,
        }

        # Filter on status
        resp = admin.client.get('/hails/?status=finished')
        assert resp.status_code == 200
        assert len(resp.json['data']) == 2

        # Filter on date
        resp = admin.client.get('/hails/?date=1988/12/03')
        assert resp.status_code == 200
        assert len(resp.json['data']) == 0

        # Admin user, with filter on operateur
        resp = admin.client.get('/hails/?operateur=%s' % operateur.user.email)
        assert resp.status_code == 200
        assert len(resp.json['data']) == 2

        # Admin user, with filter on moteur
        resp = admin.client.get('/hails/?moteur=%s' % moteur.user.email)
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1

        # Filter on taxi id
        resp = admin.client.get('/hails/?taxi_id=no')
        assert resp.status_code == 200
        assert len(resp.json['data']) == 0

        # Filter on customer_id
        resp = admin.client.get('/hails/?customer_id=%s' % hail1.customer_id)
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1

    def test_old_hail(self, admin, moteur, operateur):
        HailFactory(
            operateur=operateur.user,
            added_by=moteur.user,
            added_at=datetime.now() - timedelta(60)
        )

        resp = moteur.client.get('/hails')
        assert resp.status_code == 200
        assert len(resp.json['data']) == 0

        resp = operateur.client.get('/hails')
        assert resp.status_code == 200
        assert len(resp.json['data']) == 0

        resp = admin.client.get('/hails')
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1


class TestCreateHail:

    @staticmethod
    def _create_hail(app, operateur, moteur, customer_id='some user', session_id=None, customer_address='23 avenue de Ségur, 75007 Paris'):
        taxi = TaxiFactory(added_by=operateur.user)
        taxi_id = taxi.id

        # Simulate search before hailing
        if app.config.get('FAKE_TAXI_ID'):
            taxi_id = utils.get_short_uuid()
            app.redis.hset(
                f'fake_taxi_id:{moteur.user.email}',
                mapping={taxi_id: taxi.id}
            )

        # Report recent location in redis
        app.redis.hset(
            'taxi:%s' % taxi.id,
            operateur.user.email,
            '%s 48.84 2.35 free phone 2' % int(time.time())
        )

        with mock.patch.object(tasks.send_request_operator, 'apply_async') as mocked:
            resp = moteur.client.post('/hails', json={
                'data': [{
                    'customer_address': customer_address,
                    'customer_id': customer_id,
                    'customer_lon': 2.3098,
                    'customer_lat': 48.851,
                    'customer_phone_number': '+336868686',
                    'taxi_id': taxi_id,
                    'operateur': "chauffeur professionnel",
                    'session_id': session_id,
                }]
            })
            if resp.status_code == '201':
                assert mocked.call_count == 1

        return resp

    def test_invalid(self, anonymous, operateur):
        # Login required
        resp = anonymous.client.post('/hails', json={})
        assert resp.status_code == 401

        # Must be moteur to create hail request
        resp = operateur.client.post('/hails', json={})
        assert resp.status_code == 403

    def test_ko(self, app, moteur, operateur):
        """Test various non-working cases:

        - when customer is banned
        - when taxi's location is not in redis
        - when location is too old
        - when taxi is off
        """
        banned_customer = CustomerFactory(
            added_by=moteur.user,
            ban_begin=sqlalchemy.func.NOW(),
            ban_end=sqlalchemy.func.NOW() + timedelta(hours=+24),
        )
        taxi = TaxiFactory(added_by=operateur.user, vehicle__descriptions__status='off')

        def _create_hail(customer_id='customer_ok'):
            resp = moteur.client.post('/hails', json={
                'data': [{
                    'customer_address': '23 avenue de Ségur, 75007 Paris',
                    'customer_id': customer_id,
                    'customer_lon': 2.3098,
                    'customer_lat': 48.851,
                    'customer_phone_number': '+336868686',
                    'taxi_id': taxi.id,
                    'operateur': 'chauffeur professionnel',
                }]
            })
            return resp

        # Error: taxi location is not reported in redis
        resp = _create_hail(customer_id=banned_customer.id)
        assert resp.status_code == 403
        assert 'customer_id' in resp.json['errors']['data']['0']

        # Error: taxi location is not reported in redis
        resp = _create_hail()
        assert resp.status_code == 400
        assert resp.json['errors']['data']['0']['taxi_id'] == ['Taxi is not online.']

        # Report outdated location in redis in the past
        app.redis.hset(
            'taxi:%s' % taxi.id,
            operateur.user.email,
            '%s 48.84 2.35 free phone 2' % int(time.time() - 86400)
        )

        # Error: taxi location is not recent
        resp = _create_hail()
        assert resp.status_code == 400
        assert resp.json['errors']['data']['0']['taxi_id'] == ['Taxi is no longer online.']

        # Report recent location in redis (but taxi's vehicle description has
        # been created with status='off')
        app.redis.hset(
            'taxi:%s' % taxi.id,
            operateur.user.email,
            '%s 48.84 2.35 free phone 2' % int(time.time())
        )
        resp = _create_hail()
        assert resp.status_code == 400
        assert resp.json['errors']['data']['0']['taxi_id'] == ['Taxi is not free.']

    def test_ok(self, app, moteur, operateur):

        resp = self._create_hail(app, operateur, moteur)

        assert resp.status_code == 201
        assert 'id' in resp.json['data'][0]
        # Hail is assigned a new session ID
        assert resp.json['data'][0]['session_id'] is not None

        # Hail is logged to redis
        hail_id = resp.json['data'][0]['id']
        assert len(app.redis.zrange('hail:%s' % hail_id, 0, -1)) == 1

        # Check transition log
        hail = Hail.query.one()
        assert hail.operateur_id == operateur.user.id
        assert hail.transition_log[-1]['from_status'] is None
        assert hail.transition_log[-1]['to_status'] == 'received'
        assert hail.transition_log[-1]['user'] == moteur.user.id

    def test_automatic_session_id(self, app, moteur, operateur):
        hail = HailFactory(
            operateur=operateur.user, added_by=moteur.user,
            last_status_change=datetime.now(),
            session_id=uuid.uuid4()
        )

        # Another hail from the same user
        resp = self._create_hail(app, operateur, moteur, hail.customer_id)
        assert resp.status_code == 201, resp.json
        # Identified as the same session from the same user
        assert resp.json['data'][0]['session_id'] == str(hail.session_id)

        # Another hail with the same session ID
        resp = self._create_hail(app, operateur, moteur, hail.customer_id, hail.session_id)
        assert resp.status_code == 201, resp.json
        assert resp.json['data'][0]['session_id'] == str(hail.session_id)

        # Another hail from a different user of the same moteur
        resp = self._create_hail(app, operateur, moteur, 'other_user')
        assert resp.status_code == 201, resp.json
        assert resp.json['data'][0]['session_id'] != str(hail.session_id)

    def test_unknown_session_id(self, app, moteur, operateur):
        """Receiving a session ID not coming from us."""

        # No prior customer hail with that session ID
        resp = self._create_hail(app, operateur, moteur, 'other_user', uuid.uuid4())

        assert resp.status_code == 400, resp.json
        assert 'session_id' in resp.json['errors']['data']['0']

    def test_invalid_session_id(self, app, moteur, operateur):
        """Session ID not associated to this customer rejected"""
        hail = HailFactory(
            operateur=operateur.user, added_by=moteur.user,
            last_status_change=datetime.now(),
            session_id=uuid.uuid4()
        )

        # Reuse someone's session ID
        resp = self._create_hail(app, operateur, moteur, 'other_user', hail.session_id)

        assert resp.status_code == 400, resp.json
        assert 'session_id' in resp.json['errors']['data']['0']

    def test_old_session_id(self, app, moteur, operateur):
        """Search engine using a session ID older than our default 5 min."""
        # The customer already tried to hail a taxi an hour ago
        session_id = uuid.uuid4()
        hail = HailFactory(
            operateur=operateur.user, added_by=moteur.user,
            last_status_change=datetime.now() - timedelta(hours=1),
            session_id=session_id
        )

        # Reuse this customer's session ID
        resp = self._create_hail(app, operateur, moteur, hail.customer_id, hail.session_id)

        # Session ID reused anyway as we trust the search engine
        assert resp.status_code == 201, resp.json
        assert resp.json['data'][0]['session_id'] == str(session_id)

    def test_new_session_id(self, app, moteur, operateur):
        """Hail too far away in the past is not automatically reused."""
        session_id = uuid.UUID('19f43a74-bd60-4464-a3f4-75bb916783c0')
        hail = HailFactory(
            operateur=operateur.user, added_by=moteur.user,
            last_status_change=datetime.now() - timedelta(hours=1),
            session_id=session_id,
        )

        # Let the API generate another session ID after some time
        resp = self._create_hail(app, operateur, moteur, hail.customer_id)

        assert resp.status_code == 201, resp.json
        assert resp.json['data'][0]['session_id'] != str(session_id)

    def test_fake_taxi_id(self, app, moteur, operateur):
        app.config['FAKE_TAXI_ID'] = True
        resp = self._create_hail(app, operateur, moteur)
        assert resp.status_code == 201
        hail = Hail.query.one()
        # Real taxi ID not exposed
        assert resp.json['data'][0]['taxi']['id'] != hail.taxi_id
        # Fake taxi ID exposed instead
        assert resp.json['data'][0]['taxi']['id'] == hail.fake_taxi_id
        # Same when fetching the hail
        resp = moteur.client.get(f"/hails/{resp.json['data'][0]['id']}")
        assert resp.json['data'][0]['taxi']['id'] != hail.taxi_id
        assert resp.json['data'][0]['taxi']['id'] == hail.fake_taxi_id

    def test_fake_taxi_id_moteur_and_operateur(self, app, moteur_and_operateur):
        app.config['FAKE_TAXI_ID'] = True
        resp = self._create_hail(app, moteur_and_operateur, moteur_and_operateur)
        assert resp.status_code == 201
        hail = Hail.query.one()
        # Real taxi ID exposed
        assert resp.json['data'][0]['taxi']['id'] == hail.taxi_id
        # Fake taxi ID not used
        assert resp.json['data'][0]['taxi']['id'] != hail.fake_taxi_id
        # Same when fetching the hail
        resp = moteur_and_operateur.client.get(f"/hails/{resp.json['data'][0]['id']}")
        assert resp.json['data'][0]['taxi']['id'] == hail.taxi_id
        assert resp.json['data'][0]['taxi']['id'] != hail.fake_taxi_id

    def test_no_customer_address(self, app, moteur, operateur):
        def requests_get(*args, **kwargs):
            # From the docs
            content = {
                "type":"FeatureCollection",
                "version":"draft",
                "features":[
                    {
                        "type":"Feature",
                        "geometry":{
                            "type":"Point",
                            "coordinates":[2.290084, 49.897443]
                        },
                        "properties":{
                            "label":"8 Boulevard du Port 80000 Amiens",
                            "score":0.49159121588068583,
                            "housenumber":"8",
                            "id":"80021_6590_00008",
                            "type":"housenumber",
                            "name":"8 Boulevard du Port",
                            "postcode":"80000",
                            "citycode":"80021",
                            "x":648952.58,
                            "y":6977867.25,
                            "city":"Amiens",
                            "context":"80, Somme, Hauts-de-France",
                            "importance":0.6706612694243868,
                            "street":"Boulevard du Port"
                        }
                    }
                ],
                "attribution":"BAN",
                "licence":"ODbL 1.0",
                "query":"8 bd du port",
                "limit":1
            }
            resp = requests.Response()
            resp.status_code = 200
            resp._content = json.dumps(content).encode('utf8')
            return resp

        with mock.patch('requests.get', requests_get) as mocked:
            resp = self._create_hail(app, operateur, moteur, customer_address='')
            assert resp.status_code == 201
            assert resp.json['data'][0]['customer_address'] == "8 Boulevard du Port, Amiens"

    def test_no_customer_address_failure(self, app, moteur, operateur):
        with mock.patch('requests.get') as mocked:
            mocked.side_effect = requests.Timeout()
            resp = self._create_hail(app, operateur, moteur, customer_address='')
            assert resp.status_code == 400
            assert 'customer_address' in resp.json['errors']['data']['0']
