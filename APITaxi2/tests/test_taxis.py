from APITaxi_models2.unittest.factories import (
    HailFactory,
    TaxiFactory,
    VehicleFactory,
    VehicleDescriptionFactory,
)


class TestTaxiGet:
    def test_get_taxis_invalid(self, anonymous, moteur, operateur):
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
