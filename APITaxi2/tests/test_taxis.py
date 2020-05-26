import time

from sqlalchemy.orm import joinedload

from APITaxi_models2 import db, VehicleDescription
from APITaxi_models2.unittest.factories import (
    HailFactory,
    TaxiFactory,
    VehicleFactory,
    VehicleDescriptionFactory,
)


class TestTaxiDetails:
    def test_details_invalid(self, anonymous, moteur, operateur):
        """Tests shared for PUT /taxis/:id and GET /taxis/:id."""
        # Login required
        resp = anonymous.client.get('/taxis/xxx')
        assert resp.status_code == 401

        # Permissions denied
        resp = moteur.client.get('/taxis/xxx')
        assert resp.status_code == 403

        # Not found
        resp = operateur.client.get('/taxis/xxxx')
        assert resp.status_code == 404
        assert 'url' in resp.json['errors']

        # Taxi OK, but its "added_by" field is different from "operateur"
        taxi = TaxiFactory()
        resp = operateur.client.get('/taxis/%s' % taxi.id)
        assert resp.status_code == 404
        assert 'url' in resp.json['errors']

        # Taxi OK, but there is no VehicleDescription linked to the operateur.
        vehicle = VehicleFactory(descriptions=[])
        taxi = TaxiFactory(added_by=operateur.user, vehicle=vehicle)
        resp = operateur.client.get('/taxis/%s' % taxi.id)
        assert resp.status_code == 404
        assert 'url' in resp.json['errors']



class TestTaxiGet:
    def test_get_taxis_no_entry_in_redis(self, operateur):
        """Taxi exists but there is no entry in redis with its position."""
        taxi = TaxiFactory(added_by=operateur.user)

        resp = operateur.client.get('/taxis/%s' % taxi.id)
        assert resp.status_code == 200
        assert resp.json.get('data')
        data = resp.json['data'][0]

        assert data['id'] == taxi.id
        # last_update and position are stored in redis. They are none since no
        # entry is set in redis.
        assert data['last_update'] is None
        assert data['position']['lon'] is None
        assert data['position']['lat'] is None
        assert data['vehicle']['licence_plate'] == taxi.vehicle.licence_plate

    def test_get_taxis_multiple_operators(self, admin, operateur):
        """Taxi has several operators. Make sure the infor returned are the
        correct ones."""
        taxi = TaxiFactory(added_by=operateur.user)
        # Add a desription for this taxi for another operator
        VehicleDescriptionFactory(vehicle=taxi.vehicle, added_by=admin.user)

        resp = operateur.client.get('/taxis/%s' % taxi.id)
        assert resp.status_code == 200
        assert resp.json['data'][0]['operator'] == operateur.user.email

        resp = admin.client.get('/taxis/%s' % taxi.id)
        assert resp.status_code == 200
        assert resp.json['data'][0]['operator'] == admin.user.email

    def test_get_taxis_ok(self, app, operateur, QueriesTracker):
        taxi = TaxiFactory(added_by=operateur.user)

        # Store taxi position
        app.redis.hset('taxi:%s' % taxi.id, operateur.user.email,
            '1589567716 48.84 2.35 free phone 2'
        )

        with QueriesTracker() as qtracker:
            resp = operateur.client.get('/taxis/%s' % taxi.id)
            # SELECT permissions, SELECT taxi (joinedload all other resources)
            assert qtracker.count == 2

        assert resp.status_code == 200
        assert resp.json['data'][0]['last_update'] == 1589567716
        assert resp.json['data'][0]['position']['lat'] == 48.84
        assert resp.json['data'][0]['position']['lon'] == 2.35


class TestTaxiPut:
    def test_put_taxis_ok(self, app, operateur):
        def _set_taxi_status(status, hail=None):
            taxi = TaxiFactory(added_by=operateur.user, current_hail=hail)
            resp = operateur.client.put('/taxis/%s' % taxi.id, json={
                'data': [{
                    'status': status
                }]
            })
            return taxi, resp

        taxi, resp = _set_taxi_status('off')
        assert resp.status_code == 200
        # Taxi is in not_available list
        assert app.redis.zscore(
            'not_available',
            '%s:%s' % (taxi.id, operateur.user.email)
        ) is not None
        # Check log entry
        assert len(app.redis.zrange('taxi_status:%s' % taxi.id, 0, -1)) == 1

        taxi, resp = _set_taxi_status('free')
        assert resp.status_code == 200
        # Taxi is in not not_available list
        assert app.redis.zscore(
            'not_available',
            '%s:%s' % (taxi.id, operateur.user.email)
        ) is None
        # Check log entry
        assert len(app.redis.zrange('taxi_status:%s' % taxi.id, 0, -1)) == 1

        # Taxi is changing the status to "off" with a customer on board
        hail = HailFactory(status='customer_on_board')
        taxi, resp = _set_taxi_status('off', hail)
        assert resp.status_code == 200
        assert hail.status == 'finished'

        # Taxi is changing the status to "occupied" after driving to a customer
        hail = HailFactory(status='accepted_by_customer')
        taxi, resp = _set_taxi_status('occupied', hail)
        assert resp.status_code == 200
        assert hail.status == 'customer_on_board'
