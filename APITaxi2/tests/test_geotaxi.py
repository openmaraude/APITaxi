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

    def test_ok(self, operateur, app, QueriesTracker):
        taxi = factories.TaxiFactory(added_by=operateur.user)
        with QueriesTracker() as qtracker:
            response = operateur.client.post('/geotaxi', json={
                'data': [{
                    'positions': [{'taxi_id': taxi.id, 'lon': 2.35, 'lat': 48.86}]
                }]
            })
            assert response.status_code == 200
            # SELECT permissions, SELECT taxi (writing is done in Redis)
            assert qtracker.count == 2

        # There should be five keys stored (after the IP index was dropped)
        taxi_key = taxi.id.encode()
        operator_key = operateur.user.email.encode()
        taxi_operator_key = b'%s:%s' % (taxi_key, operator_key)
        assert set(app.redis.keys()) == {
            b'taxi:%s' % taxi_key,
            b'geoindex',
            b'geoindex_2',
            b'timestamps',
            b'timestamps_id',
        }

        assert operator_key in app.redis.hgetall(b'taxi:%s' % taxi_key)
        assert app.redis.geohash(b'geoindex', taxi_key) == ['u09tvqxnnu0']
        assert app.redis.geohash(b'geoindex_2', taxi_operator_key) == ['u09tvqxnnu0']
        assert app.redis.zrange(b'timestamps', 0, -1) == [taxi_operator_key]
        assert app.redis.zrange(b'timestamps_id', 0, -1) == [taxi_key]

        # High-level API
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

    def test_ok_taxi_two_operators(self, app, operateur, QueriesTracker):
        """Taxi is registered with two operators, but reports its location with
        only one.
        """
        vehicle = factories.VehicleFactory(descriptions=[])
        factories.VehicleDescriptionFactory(
            vehicle=vehicle,
            added_by=operateur.user,
        )
        # VehicleDescription related to another operator
        factories.VehicleDescriptionFactory(
            vehicle=vehicle,
        )
        taxi = factories.TaxiFactory(vehicle=vehicle)

        with QueriesTracker() as qtracker:
            response = operateur.client.post('/geotaxi', json={
                'data': [{
                    'positions': [{'taxi_id': taxi.id, 'lon': 2.35, 'lat': 48.86}]
                }]
            })
            assert response.status_code == 200
            # SELECT permissions, SELECT taxi (writing is done in Redis)
            assert qtracker.count == 2
