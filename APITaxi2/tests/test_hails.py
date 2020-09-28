from datetime import timedelta
import time
from unittest import mock

import sqlalchemy

from APITaxi2 import tasks
from APITaxi_models2 import Taxi, Vehicle, VehicleDescription
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
        # Hail exists, user is not the moteur nor the operateur but he has the
        # admin role.
        hail = HailFactory()
        resp = admin.client.get('/hails/%s' % hail.id)
        assert resp.status_code == 200

        # Hail exists and user is the moteur
        hail = HailFactory(added_by=moteur.user)
        resp = moteur.client.get('/hails/%s' % hail.id)
        assert resp.status_code == 200

        # Hail exists and user is the operateur
        hail = HailFactory(operateur=operateur.user)
        resp = operateur.client.get('/hails/%s' % hail.id)
        assert resp.status_code == 200

        # Position exists in redis and hail is in progress: location is returned
        hail = HailFactory(status='customer_on_board', added_by=moteur.user, operateur=operateur.user)
        app.redis.hset(
            'taxi:%s' % hail.taxi.id,
            hail.added_by.email,
            '1589567716 48.84 2.35 free phone 2'
        )
        with QueriesTracker() as qtracker:
            resp = moteur.client.get('/hails/%s' % hail.id)
            # SELECT permissions, SELECT hail
            assert qtracker.count == 2
        assert resp.status_code == 200
        assert resp.json['data'][0]['taxi']['crowfly_distance']
        assert resp.json['data'][0]['taxi']['last_update']
        assert resp.json['data'][0]['taxi']['position']['lon']
        assert resp.json['data'][0]['taxi']['position']['lat']
        # For backward compatibility, taxi_id is not returned from GET
        # /hails/:id, but the field is required to create a taxi with POST
        # /hails/:id
        assert 'taxi_id' not in resp.json['data'][0]

        # Position exists in redis and hail is finished: location is not returned
        hail = HailFactory(status='finished', added_by=moteur.user, operateur=operateur.user)
        app.redis.hset(
            'taxi:%s' % hail.taxi.id,
            hail.added_by.email,
            '1589567716 48.84 2.35 free phone 2'
        )
        resp = moteur.client.get('/hails/%s' % hail.id)
        assert resp.status_code == 200
        assert not resp.json['data'][0]['taxi']['crowfly_distance']
        assert not resp.json['data'][0]['taxi']['last_update']
        assert not resp.json['data'][0]['taxi']['position']['lon']
        assert not resp.json['data'][0]['taxi']['position']['lat']


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

        resp = operateur.client.put('/hails/%s' % hail.id, json={'data': [{
            'status': 'accepted_by_taxi',
            'taxi_phone_number': '+33600000000'
        }]})

        assert resp.status_code == 200
        assert resp.json['data'][0]['id'] == hail.id
        assert resp.json['data'][0]['status'] == 'accepted_by_taxi'
        assert resp.json['data'][0]['taxi_phone_number'] == '+33600000000'

        # When the hail's status changes to "accepted_by_taxi", taxi's status
        # becomes "incoming".
        assert VehicleDescription.query.join(Vehicle).join(Taxi).filter(
            Taxi.id == hail.taxi_id
        ).one().status == 'oncoming'

        # Make sure request is logged
        assert len(app.redis.zrange('hail:%s' % hail.id, 0, -1)) == 1

    def test_change_operateur_param_by_moteur(self, moteur, operateur):
        """Moteur attempts to change a field that can only be updated by an
        operateur."""
        hail = HailFactory(operateur=operateur.user, added_by=moteur.user, status='accepted_by_taxi')

        resp = moteur.client.put('/hails/%s' % hail.id, json={'data': [{
            'incident_taxi_reason': 'no_show'
        }]})
        assert resp.status_code == 400
        assert len(resp.json['errors']['data']['0']['incident_taxi_reason']) == 1

    def test_ok_change_operateur_ban_customer(self, moteur, operateur):
        # Create unbanned customer
        customer = CustomerFactory(moteur=moteur.user, ban_begin=None, ban_end=None,)
        hail = HailFactory(customer=customer, added_by=moteur.user,
                           operateur=operateur.user,
                           status='accepted_by_taxi')
        # Ban
        resp = operateur.client.put('/hails/%s' % hail.id, json={'data': [{
            'incident_taxi_reason': 'no_show',
            'reporting_customer': True
        }]})
        assert resp.status_code == 200
        assert customer.ban_begin
        assert customer.ban_end

    def test_ok_change_operateur_unban_customer(self, moteur, operateur):
        # Create banned customer
        customer = CustomerFactory(
            moteur=moteur.user,
            ban_begin=sqlalchemy.func.NOW(),
            ban_end=sqlalchemy.func.NOW() + timedelta(hours=+24),
        )
        assert customer.ban_begin
        assert customer.ban_end
        # Unban
        hail = HailFactory(customer=customer, added_by=moteur.user,
                           operateur=operateur.user,
                           status='accepted_by_taxi')
        resp = operateur.client.put('/hails/%s' % hail.id, json={'data': [{
            'reporting_customer': False
        }]})
        assert resp.status_code == 200
        assert not customer.ban_begin
        assert not customer.ban_end

    def test_change_moteur_param_by_operateur(self, moteur, operateur):
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
        HailFactory(operateur=operateur.user, status='received')
        HailFactory(operateur=operateur.user, status='finished')
        HailFactory(added_by=moteur.user, status='finished')

        # Admin get all hails
        with QueriesTracker() as qtracker:
            resp = admin.client.get('/hails/')
            # Get permissions, list hails. Depending on version, COUNT(*) for
            # pagination.
            assert qtracker.count <= 3

        assert resp.status_code == 200
        assert len(resp.json['data']) == 3

        # Operateur gets only its hails
        resp = operateur.client.get('/hails/')
        assert resp.status_code == 200
        assert len(resp.json['data']) == 2

        # Moteur gets only its hails
        resp = moteur.client.get('/hails/')
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1

        # Pagination information is returned
        resp = admin.client.get('/hails/')
        assert resp.status_code == 200
        assert resp.json['meta'] == {
            'next_page': None,
            'prev_page': None,
            'pages': 1,
            'total': 3
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


class TestCreateHail:
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
            moteur=moteur.user,
            ban_begin=sqlalchemy.func.NOW(),
            ban_end=sqlalchemy.func.NOW() + timedelta(hours=+24),
        )
        vehicle = VehicleFactory()
        VehicleDescriptionFactory(vehicle=vehicle, added_by=operateur.user, status='off')
        taxi = TaxiFactory(added_by=operateur.user, vehicle=vehicle)

        def _create_hail(customer_id='customer_ok'):
            resp = moteur.client.post('/hails', json={
                'data': [{
                    'customer_address': '23 avenue de Ségur, 75007 Paris',
                    'customer_id': customer_id,
                    'customer_lon': 2.3098,
                    'customer_lat': 48.851,
                    'customer_phone_number': '+336868686',
                    'taxi_id': taxi.id,
                    'operateur': operateur.user.email
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
        taxi = TaxiFactory(added_by=operateur.user)

        # Report recent location in redis
        app.redis.hset(
            'taxi:%s' % taxi.id,
            operateur.user.email,
            '%s 48.84 2.35 free phone 2' % int(time.time())
        )

        with mock.patch.object(tasks.send_request_operator, 'apply_async') as mocked:
            resp = moteur.client.post('/hails', json={
                'data': [{
                    'customer_address': '23 avenue de Ségur, 75007 Paris',
                    'customer_id': 'Lucky Luke',
                    'customer_lon': 2.3098,
                    'customer_lat': 48.851,
                    'customer_phone_number': '+336868686',
                    'taxi_id': taxi.id,
                    'operateur': operateur.user.email
                }]
            })
            assert mocked.call_count == 1

        assert resp.status_code == 201
        assert 'id' in resp.json['data'][0]

        # Hail is logged to redis
        hail_id = resp.json['data'][0]['id']
        assert len(app.redis.zrange('hail:%s' % hail_id, 0, -1)) == 1

        # Hail is logged to influxdb
        assert len(list(app.influx.measurement.tag_values(measurement='hails_created', key='operator'))) == 1
