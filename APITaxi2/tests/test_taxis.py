from datetime import datetime, timedelta
import time

from sqlalchemy.orm import lazyload

from APITaxi_models2 import db, Taxi, Vehicle, VehicleDescription
from APITaxi_models2.unittest.factories import (
    ADSFactory,
    DriverFactory,
    HailFactory,
    TaxiFactory,
    VehicleFactory,
    VehicleDescriptionFactory,
    ZUPCFactory,
)


class TestTaxiDetails:
    def test_invalid(self, anonymous, moteur, operateur):
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
    def test_no_entry_in_redis(self, operateur):
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

    def test_multiple_operators(self, admin, operateur):
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

    def test_ok(self, app, operateur, QueriesTracker):
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
    def test_ok(self, app, operateur):
        def _set_taxi_status(status, hail=None, initial_status=None):
            taxi = TaxiFactory(added_by=operateur.user, current_hail=hail)

            # If initial_status is set, fetch the VehicleDescription linked to
            # taxi and set its status to the value. By default,
            # VehicleDescriptionFactory initializes the status to "free".
            if initial_status:
                query = VehicleDescription.query.options(lazyload('*')).join(
                    Vehicle
                ).join(
                    Taxi
                ).filter(Taxi.id == taxi.id)

                vehicle_description = query.one()
                vehicle_description.status = initial_status
                db.session.commit()

            #if initial_status:
            #    taxi.vehicle.descriptions[0].status = initial_status
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

        taxi, resp = _set_taxi_status('free', initial_status='off')
        assert resp.status_code == 200
        # Taxi is in not not_available list
        assert app.redis.zscore(
            'not_available',
            '%s:%s' % (taxi.id, operateur.user.email)
        ) is None
        # Check log entry
        assert len(app.redis.zrange('taxi_status:%s' % taxi.id, 0, -1)) == 1

        # If the status is the same, nothing is logged.
        taxi, resp = _set_taxi_status('free', initial_status='free')
        assert len(app.redis.zrange('taxi_status:%s' % taxi.id, 0, -1)) == 0

        # Taxi is changing the status to "off" with a customer on board
        hail = HailFactory(status='customer_on_board')
        taxi, resp = _set_taxi_status('off', hail=hail)
        assert resp.status_code == 200
        assert hail.status == 'finished'

        # Taxi is changing the status to "occupied" after driving to a customer
        hail = HailFactory(status='accepted_by_customer')
        taxi, resp = _set_taxi_status('occupied', hail=hail)
        assert resp.status_code == 200
        assert hail.status == 'customer_on_board'


class TestTaxiPost:
    def test_invalid(self, operateur):
        resp = operateur.client.post('/taxis', json={
            'data': [{}]
        })
        assert resp.status_code == 400
        # Required fields
        assert 'ads' in resp.json['errors']['data']['0']
        assert 'vehicle' in resp.json['errors']['data']['0']
        assert 'driver' in resp.json['errors']['data']['0']

        # Valid request, but non-existing items
        resp = operateur.client.post('/taxis', json={
            'data': [{
                'ads': {
                    'insee': 'aaa',
                    'numero': 'bbb'
                },
                'vehicle': {
                    'licence_plate': 'cccc'
                },
                'driver': {
                    'professional_licence': 'ddd',
                    'departement': 'eee'
                }
            }]
        })
        assert resp.status_code == 404
        assert 'insee' in resp.json['errors']['data']['0']['ads']
        assert 'numero' in resp.json['errors']['data']['0']['ads']
        assert 'licence_plate' in resp.json['errors']['data']['0']['vehicle']
        assert 'departement' in resp.json['errors']['data']['0']['driver']
        assert 'professional_licence' in resp.json['errors']['data']['0']['driver']

    def test_vehicle_description_other_user(self, operateur):
        """Vehicle exists, but there is no VehicleDescription entry for the user making request."""
        ads = ADSFactory()
        driver = DriverFactory()
        # VehicleFactory creates a VehicleDescription linked to a new user.
        vehicle_from_other_user = VehicleFactory()
        resp = operateur.client.post('/taxis', json={
            'data': [{
                'ads': {
                    'insee': ads.insee,
                    'numero': ads.numero
                },
                'vehicle': {
                    'licence_plate': vehicle_from_other_user.licence_plate
                },
                'driver': {
                    'professional_licence': driver.professional_licence,
                    'departement': driver.departement.numero
                }
            }]
        })
        assert resp.status_code == 404
        assert (resp.json['errors']['data']['0']['vehicle']['licence_plate']
            == ['Vehicle exists but has not been created by the user making the request'])

    def test_departement_not_found(self, operateur):
        ads = ADSFactory()
        driver = DriverFactory()
        vehicle_description = VehicleDescriptionFactory(added_by=operateur.user)

        resp = operateur.client.post('/taxis', json={
            'data': [{
                'ads': {
                    'insee': ads.insee,
                    'numero': ads.numero
                },
                'vehicle': {
                    'licence_plate': vehicle_description.vehicle.licence_plate
                },
                'driver': {
                    'professional_licence': driver.professional_licence,
                    'departement': 'xxxx'
                }
            }]
        })
        assert resp.status_code == 404
        assert resp.json['errors']['data']['0']['driver']['departement'] == ['Departement not found']

    def test_departement_ok_driver_invalid(self, operateur):
        ads = ADSFactory()
        driver = DriverFactory()
        vehicle_description = VehicleDescriptionFactory(added_by=operateur.user)

        resp = operateur.client.post('/taxis', json={
            'data': [{
                'ads': {
                    'insee': ads.insee,
                    'numero': ads.numero
                },
                'vehicle': {
                    'licence_plate': vehicle_description.vehicle.licence_plate
                },
                'driver': {
                    'professional_licence': 'invalid',
                    'departement': driver.departement.numero
                }
            }]
        })
        assert resp.status_code == 404
        assert list(resp.json['errors']['data']['0']['driver'].keys()) == ['professional_licence']

    def test_ok(self, operateur, QueriesTracker):
        ads = ADSFactory()
        driver = DriverFactory()
        vehicle_description = VehicleDescriptionFactory(added_by=operateur.user)

        payload = {
            'data': [{
                'ads': {
                    'insee': ads.insee,
                    'numero': ads.numero
                },
                'vehicle': {
                    'licence_plate': vehicle_description.vehicle.licence_plate
                },
                'driver': {
                    'professional_licence': driver.professional_licence,
                    'departement': driver.departement.numero
                }
            }]
        }

        assert Taxi.query.count() == 0

        with QueriesTracker() as qtracker:
            resp = operateur.client.post('/taxis', json=payload)
            # Queries:
            # - permissions
            # - SELECT ADS
            # - SELECT vehicle
            # - SELECT departement
            # - SELECT driver
            # - SELECT taxi to check if it exists
            # - INSERT taxi
            assert qtracker.count == 7

        assert resp.status_code == 201
        assert Taxi.query.count() == 1

        # Same request, no taxi created
        resp = operateur.client.post('/taxis', json=payload)
        assert resp.status_code == 200
        assert Taxi.query.count() == 1


class TestTaxiList:

    def test_invalid(self, anonymous, operateur):
        # Login required
        resp = anonymous.client.get('/taxis')
        assert resp.status_code == 401

        # Permission denied
        resp = operateur.client.get('/taxis')
        assert resp.status_code == 403

    def test_ok(self, app, moteur):
        zupc = ZUPCFactory()
        now = datetime.now()

        taxi_1 = TaxiFactory(ads__zupc=zupc)

        taxi_2_vehicle = VehicleFactory(descriptions=[])

        # When a taxi has several descriptions, the default is the one that has
        # been updated for the last time.
        taxi_2_vehicle_descriptions_1 = VehicleDescriptionFactory(
            vehicle=taxi_2_vehicle,
            last_update_at=now
        )
        taxi_2_vehicle_descriptions_2 = VehicleDescriptionFactory(
            vehicle=taxi_2_vehicle,
            last_update_at=now - timedelta(days=15)
        )

        taxi_2 = TaxiFactory(ads__zupc=zupc, vehicle=taxi_2_vehicle)

        lon = tmp_lon = 2.35
        lat = tmp_lat = 48.86

        resp = moteur.client.get('/taxis?lon=%s&lat=%s' % (lon, lat))
        assert resp.status_code == 200
        assert resp.json['data'] == []

        # Insert locations for each operator.
        for taxi in Taxi.query.options(lazyload('*')):
            for description in VehicleDescription.query.options(
                lazyload('*')
            ).filter_by(
                vehicle=taxi.vehicle
            ).order_by(
                VehicleDescription.id
            ):
                app.redis.geoadd(
                    'geoindex_2',
                    tmp_lon,
                    tmp_lat,
                    '%s:%s' % (taxi.id, description.added_by.email)
                )
                app.redis.zadd(
                    'timestamps', {
                        '%s:%s' % (taxi.id, description.added_by.email): int(time.time())
                    }
                )

                # Move taxi a little bit further
                tmp_lon += 0.0001
                tmp_lat += 0.0001

        resp = moteur.client.get('/taxis?lon=%s&lat=%s' % (lon, lat))
        assert resp.status_code == 200
        assert len(resp.json['data']) == 2
        # First is closer
        assert resp.json['data'][0]['crowfly_distance'] < resp.json['data'][1]['crowfly_distance']
        assert resp.json['data'][1]['operator'] == taxi_2_vehicle_descriptions_1.added_by.email

        # If favorite_operator is set, do not return the default.
        resp = moteur.client.get('/taxis?lon=%s&lat=%s&favorite_operator=%s' % (
            lon, lat, taxi_2_vehicle_descriptions_2.added_by.email
        ))
        assert resp.status_code == 200
        assert len(resp.json['data']) == 2
        assert resp.json['data'][1]['operator'] == taxi_2_vehicle_descriptions_2.added_by.email

        # Search for a location still in the ZUPC, but too far to reach taxis.
        resp = moteur.client.get('/taxis?lon=%s&lat=%s' % (lon + 0.02 , lat + 0.01))
        assert resp.status_code == 200
        assert len(resp.json['data']) == 0

        # Test ?count
        resp = moteur.client.get('/taxis?lon=%s&lat=%s&count=1' % (lon, lat))
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1

        # taxi_2 reports location with two operators. The default is "off", but
        # the non-default one returns a valid location.
        taxi_2_vehicle_descriptions_1.status = 'off'
        resp = moteur.client.get('/taxis?lon=%s&lat=%s' % (lon, lat))
        assert resp.status_code == 200
        assert len(resp.json['data']) == 2

        # Both operators are not free.
        taxi_2_vehicle_descriptions_2.status = 'occupied'
        resp = moteur.client.get('/taxis?lon=%s&lat=%s' % (lon, lat))
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1

        # First taxi's location is too old.
        app.redis.zadd(
            'timestamps', {
                '%s:%s' % (taxi_1.id, taxi_1.vehicle.descriptions[0].added_by.email):
                    # 5 minutes old
                    int(time.time()) - 60 * 5
            }
        )
        resp = moteur.client.get('/taxis?lon=%s&lat=%s' % (lon, lat))
        assert resp.status_code == 200
        assert len(resp.json['data']) == 0
