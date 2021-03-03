from APITaxi_models2.unittest import factories

from APITaxi2 import redis_backend


class TestPostPositions:
    def test_invalid(self, anonymous, operateur, moteur):
        # Login required
        response = anonymous.client.post('/geotaxi', json={'data': [{'positions': []}]})
        assert response.status_code == 401

        # Only operators
        response = moteur.client.post('/geotaxi', json={'data': [{'positions': []}]})
        assert response.status_code == 403

        # Operator posting is not the owner
        taxi = factories.TaxiFactory()
        response = operateur.client.post('/geotaxi', json={
            'data': [{
                'positions': [{'taxi_id': taxi.id, 'lon': 2.35, 'lat': 48.86}]
            }]
        })
        assert response.status_code == 400
        assert 'taxi_id' in response.json['errors']['data']['0']['positions']['0']

        # Not updated
        redis_taxi = redis_backend.get_taxi(taxi.id, taxi.added_by.email)
        assert redis_taxi is None

    def test_ok(self, operateur):
        taxi = factories.TaxiFactory(added_by=operateur.user)
        response = operateur.client.post('/geotaxi', json={
            'data': [{
                'positions': [{'taxi_id': taxi.id, 'lon': 2.35, 'lat': 48.86}]
            }]
        })
        assert response.status_code == 200

        redis_taxi = redis_backend.get_taxi(taxi.id, operateur.user.email)
        assert redis_taxi
        assert redis_taxi.lon == 2.35 and redis_taxi.lat == 48.86

    def test_invalid_coordinates(self, operateur):
        taxi = factories.TaxiFactory(added_by=operateur.user)
        response = operateur.client.post('/geotaxi', json={
            'data': [{
                'positions': [{'taxi_id': taxi.id, 'lon': 612.35, 'lat': 548.86}]
            }]
        })
        assert response.status_code == 400
        # Both longitude and latitude rejected
        assert 'lon' in response.json['errors']['data']['0']['positions']['0']
        assert 'lat' in response.json['errors']['data']['0']['positions']['0']

        # Not updated
        redis_taxi = redis_backend.get_taxi(taxi.id, operateur.user.email)
        assert redis_taxi is None

    def test_outside_france(self, operateur):
        taxi = factories.TaxiFactory(added_by=operateur.user)
        response = operateur.client.post('/geotaxi', json={
            'data': [{
                'positions': [{'taxi_id': taxi.id, 'lon': 48.86, 'lat': 2.35}]  # Inverted
            }]
        })
        assert response.status_code == 200  # Accepted for now

        # Accepted for now
        redis_taxi = redis_backend.get_taxi(taxi.id, operateur.user.email)
        assert redis_taxi is not None

    def test_one_valid_one_invalid(self, operateur):
        taxi = factories.TaxiFactory(added_by=operateur.user)
        response = operateur.client.post('/geotaxi', json={
            'data': [{
                'positions': [
                    {'taxi_id': taxi.id, 'lon': 2.35, 'lat': 48.86},
                    {'taxi_id': 'dummy', 'lon': 2.35, 'lat': 48.86},
                ]
            }]
        })
        assert response.status_code == 400
        assert 'taxi_id' in response.json['errors']['data']['0']['positions']['1']

        # The valid taxi was not updated
        redis_taxi = redis_backend.get_taxi(taxi.id, operateur.user.email)
        assert redis_taxi is None

    def test_many(self, operateur):
        taxis = factories.TaxiFactory.create_batch(50, added_by=operateur.user)
        response = operateur.client.post('/geotaxi', json={
            'data': [{
                'positions': [
                    {'taxi_id': taxi.id, 'lon': 2.35, 'lat': 48.86}
                    for taxi in taxis
                ]
            }]
        })
        assert response.status_code == 200

        redis_taxi = redis_backend.get_taxi(taxis[36].id, operateur.user.email)  # Pick a random one
        assert redis_taxi
        assert redis_taxi.lon == 2.35 and redis_taxi.lat == 48.86

    def test_too_many(self, operateur):
        taxis = factories.TaxiFactory.create_batch(51, added_by=operateur.user)
        response = operateur.client.post('/geotaxi', json={
            'data': [{
                'positions': [
                    {'taxi_id': taxi.id, 'lon': 2.35, 'lat': 48.86}
                    for taxi in taxis
                ]
            }]
        })
        assert response.status_code == 400
        assert 'positions' in response.json['errors']['data']['0']
