from datetime import datetime, timedelta
import time

from sqlalchemy.orm import lazyload

from APITaxi2.exclusions import ExclusionHelper
from APITaxi_models2 import Taxi, VehicleDescription
from APITaxi_models2.stats import StatsSearches
from APITaxi_models2.unittest.factories import (
    ADSFactory,
    ExclusionFactory,
    DriverFactory,
    TaxiFactory,
    TownFactory,
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
        assert data['operator'] == operateur.user.email  # Can see the real operator

    def test_multiple_operators(self, admin, operateur):
        """Taxi has several operators. Make sure the info returned are the
        correct ones."""
        taxi = TaxiFactory(added_by=operateur.user)
        # Add a description for this taxi for another operator
        VehicleDescriptionFactory(vehicle=taxi.vehicle, added_by=admin.user)

        resp = operateur.client.get('/taxis/%s' % taxi.id)
        assert resp.status_code == 200
        assert resp.json['data'][0]['operator'] == operateur.user.email  # Can see the real operator

        resp = admin.client.get('/taxis/%s' % taxi.id)
        assert resp.status_code == 200
        assert resp.json['data'][0]['operator'] == admin.user.email  # Can see the real operator

    def test_ok(self, app, operateur, QueriesTracker):
        taxi = TaxiFactory(added_by=operateur.user)

        # Store taxi position
        app.redis.hset(
            'taxi:%s' % taxi.id,
            operateur.user.email,
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
        assert resp.json['data'][0]['operator'] == operateur.user.email  # Can see the real operator


class TestTaxiPut:
    def test_ok(self, app, operateur, QueriesTracker):
        def _set_taxi_status(status, hail=None, initial_status=None):
            vehicle = VehicleFactory(descriptions=[])
            VehicleDescriptionFactory(
                vehicle=vehicle,
                added_by=operateur.user,
                status=initial_status
            )
            taxi = TaxiFactory(vehicle=vehicle)

            with QueriesTracker() as qtracker:
                resp = operateur.client.put('/taxis/%s' % taxi.id, json={
                    'data': [{
                        'status': status
                    }]
                })
                # SELECT permissions, SELECT taxi, UPDATE hail, UPDATE vehicle_description, INSERT log, UPDATE taxi
                assert qtracker.count <= 6
            return taxi, resp

        taxi, resp = _set_taxi_status('off')
        assert resp.status_code == 200
        # Taxi is in not_available list
        assert app.redis.zscore(
            'not_available',
            '%s:%s' % (taxi.id, operateur.user.email)
        ) is not None

        taxi, resp = _set_taxi_status('free', initial_status='off')
        assert resp.status_code == 200
        # Taxi is in not not_available list
        assert app.redis.zscore(
            'not_available',
            '%s:%s' % (taxi.id, operateur.user.email)
        ) is None

        # Set the radius only
        for radius, expected_code in [(150, 200), (149, 400), (500, 200), (501, 400), (None, 200)]:
            resp = operateur.client.put('/taxis/%s' % taxi.id, json={
                'data': [{
                    'radius': radius
                }]
            })
            assert resp.status_code == expected_code, radius


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
                    'licence_plate': 'AB-123-CD',
                    'nb_seats': 4,
                    # Specifically test accepting null for strings
                    'color': None,
                    'engine': None,
                    'horodateur': None,
                    'taximetre': None,
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
                    'departement': 'xxx'
                }
            }]
        })
        assert resp.status_code == 404, resp.json
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
        ads = ADSFactory(added_by=operateur.user)
        driver = DriverFactory(added_by=operateur.user)
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
            # - SELECT permissions
            # - INSERT log
            # - SELECT ADS
            # - SELECT vehicle
            # - SELECT departement
            # - SELECT driver
            # - SELECT taxi to check if it exists
            # - INSERT taxi
            # - SELECT added_at
            assert qtracker.count == 9

        assert resp.status_code == 201
        assert Taxi.query.count() == 1

        # Same request, no taxi created
        resp = operateur.client.post('/taxis', json=payload)
        assert resp.status_code == 200
        assert Taxi.query.count() == 1

    def test_duplicates_taxi(self, operateur):
        """Taxi is identified by `ads_id`, `driver_id` and `vehicle_id`. There
        is no unique key for these fields in database, and duplicates exist. In
        case of duplicate, we should return the last one.
        """
        ads = ADSFactory(added_by=operateur.user)
        driver = DriverFactory(added_by=operateur.user)
        vehicle = VehicleFactory(descriptions=[])
        VehicleDescriptionFactory(vehicle=vehicle, added_by=operateur.user)

        TaxiFactory(ads=ads, vehicle=vehicle, driver=driver, added_by=operateur.user)

        payload = {
            'data': [{
                'ads': {
                    'insee': ads.insee,
                    'numero': ads.numero
                },
                'vehicle': {
                    'licence_plate': vehicle.licence_plate
                },
                'driver': {
                    'professional_licence': driver.professional_licence,
                    'departement': driver.departement.numero
                }
            }]
        }
        resp = operateur.client.post('/taxis', json=payload)
        assert resp.status_code == 200

    def test_empty_licence_plate(self, operateur):
        """Given but empty licence plate used to be accepted, prevent it from now"""
        ads = ADSFactory(added_by=operateur.user)
        driver = DriverFactory(added_by=operateur.user)

        payload = {
            'data': [{
                'ads': {
                    'insee': ads.insee,
                    'numero': ads.numero,
                },
                'vehicle': {
                    'licence_plate': "",
                },
                'driver': {
                    'professional_licence': driver.professional_licence,
                    'departement': driver.departement.numero
                }
            }]
        }
        resp = operateur.client.post('/taxis', json=payload)
        assert resp.status_code == 400
        assert list(resp.json['errors']['data']['0']['vehicle']) == ['licence_plate']

    def test_historical_ok(self, operateur, QueriesTracker):
        """Historical partners took bad habits from our awful docs. Until we can erase
        this technical debt, continue to accept these habits.
        """
        ads = ADSFactory(added_by=operateur.user)
        driver = DriverFactory(added_by=operateur.user)
        vehicle_description = VehicleDescriptionFactory(added_by=operateur.user)

        payload = {
            'data': [{
                'ads': {
                    'insee': ads.insee,
                    'numero': ads.numero,
                    'doublage': True,
                    'owner_name': "John Doe",
                    'owner_type': "individual",
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

        resp = operateur.client.post('/taxis', json=payload)
        assert resp.status_code == 201, resp.json


class TestTaxiSearch:

    @staticmethod
    def _post_geotaxi(app, lon, lat, taxi, vehicle_description):
        app.redis.geoadd(
            'geoindex_2',
            [
                lon,
                lat,
                '%s:%s' % (taxi.id, vehicle_description.added_by.email)
            ]
        )
        app.redis.zadd(
            'timestamps', {
                '%s:%s' % (taxi.id, vehicle_description.added_by.email): int(time.time()),
            }
        )

    def test_invalid(self, anonymous, operateur):
        # Login required
        resp = anonymous.client.get('/taxis')
        assert resp.status_code == 401

    def test_ok(self, app, moteur, QueriesTracker):
        ZUPCFactory()
        now = datetime.now()

        taxi_1 = TaxiFactory()
        taxi_1_operateur = taxi_1.added_by.email

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

        TaxiFactory(vehicle=taxi_2_vehicle)

        lon, lat = tmp_lon, tmp_lat = 2.35, 48.86
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
                self._post_geotaxi(app, tmp_lon, tmp_lat, taxi, description)
                # Move taxi a little bit further
                tmp_lon += 0.0001
                tmp_lat += 0.0001

        with QueriesTracker() as qtracker:
            resp = moteur.client.get('/taxis?lon=%s&lat=%s' % (lon, lat))
            # SELECT permissions, SELECT TOWN, SELECT ZUPC, SELECT taxi, INSERT STATS
            assert qtracker.count == 5

        assert resp.status_code == 200
        assert len(resp.json['data']) == 2
        # First is closer
        assert resp.json['data'][0]['crowfly_distance'] < resp.json['data'][1]['crowfly_distance']
        assert resp.json['data'][0]['operator'] == 'chauffeur professionnel'
        assert resp.json['data'][0]['position']['lon']
        assert resp.json['data'][0]['position']['lat']

        assert resp.json['data'][1]['operator'] == 'chauffeur professionnel'
        assert resp.json['data'][1]['position']['lon']
        assert resp.json['data'][1]['position']['lat']

        # Search for a location still in the ZUPC, but too far to reach taxis.
        resp = moteur.client.get('/taxis?lon=%s&lat=%s' % (lon + 0.02, lat + 0.01))
        assert resp.status_code == 200
        assert len(resp.json['data']) == 0

        # TODO remove Ignore obsolete ?count
        resp = moteur.client.get('/taxis?lon=%s&lat=%s&count=1' % (lon, lat))
        assert resp.status_code == 200
        assert len(resp.json['data']) == 2

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
                '%s:%s' % (taxi_1.id, taxi_1_operateur):
                    # 5 minutes old
                    int(time.time()) - 60 * 5
            }
        )
        resp = moteur.client.get('/taxis?lon=%s&lat=%s' % (lon, lat))
        assert resp.status_code == 200
        assert len(resp.json['data']) == 0

        # You can count seven client.get() above indeed
        assert StatsSearches.query.count() == 7

    def test_ok_taxi_two_operators(self, app, moteur):
        """Taxi is registered with two operators, but reports its location with
        only one.
        """
        now = datetime.now()
        vehicle = VehicleFactory(descriptions=[])

        # VehicleDescription related to an operator for which there is no
        # location update.
        VehicleDescriptionFactory(
            vehicle=vehicle,
            last_update_at=now - timedelta(days=15),
        )
        # VehicleDescription related to an operator with location update.
        vehicle_description = VehicleDescriptionFactory(
            vehicle=vehicle,
            last_update_at=now
        )

        taxi = TaxiFactory(vehicle=vehicle)
        ZUPCFactory()

        lon, lat = 2.367895, 48.86789
        self._post_geotaxi(app, lon, lat, taxi, vehicle_description)

        resp = moteur.client.get('/taxis?lon=%s&lat=%s' % (lon, lat))
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['operator'] == 'chauffeur professionnel'
        assert resp.json['data'][0]['position']['lon']
        assert resp.json['data'][0]['position']['lat']

    def test_different_zupc(self, app, moteur, operateur):
        """Request is made from Paris, and taxi reports its location in Paris
        but its ZUPC is in Bordeaux.
        """
        ZUPCFactory()  # Paris
        ZUPCFactory(bordeaux=True)

        vehicle = VehicleFactory(descriptions=[])
        vehicle_description = VehicleDescriptionFactory(vehicle=vehicle)
        # Taxi ADS is in Bordeaux.
        taxi = TaxiFactory(ads__insee='33063', vehicle=vehicle)

        # Report location in Paris.
        lon, lat = 2.367895, 48.86789
        self._post_geotaxi(app, lon, lat, taxi, vehicle_description)

        resp = moteur.client.get('/taxis?lon=%s&lat=%s' % (lon, lat))
        assert resp.status_code == 200
        # No taxi should be returned.
        assert len(resp.json['data']) == 0

    def test_ok_operateur(self, app, operateur):
        app.config['FAKE_TAXI_ID'] = False
        ZUPCFactory()  # Paris
        TaxiFactory()  # Competitor

        lon, lat = 2.35, 48.86
        now = datetime.now()
        vehicle = VehicleFactory(descriptions=[])

        # VehicleDescription related to an operator for which there is no
        # location update.
        VehicleDescriptionFactory(
            vehicle=vehicle,
            last_update_at=now - timedelta(days=15),
        )
        # VehicleDescription related to an operator with location update.
        vehicle_description = VehicleDescriptionFactory(
            vehicle=vehicle,
            last_update_at=now,
            added_by=operateur.user,
        )

        my_taxi = TaxiFactory(vehicle=vehicle)
        self._post_geotaxi(app, lon, lat, my_taxi, vehicle_description)

        # Operators can now see their own taxis, but only theirs obviously
        resp = operateur.client.get('/taxis?lon=%s&lat=%s' % (lon, lat))
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['id'] == my_taxi.id
        assert resp.json['data'][0]['operator'] == 'chauffeur professionnel'  # No exception

    def test_ok_operateur_fake_taxi_id(self, app, operateur):
        app.config['FAKE_TAXI_ID'] = True
        ZUPCFactory()
        lon, lat = 2.35, 48.86
        vehicle = VehicleFactory(descriptions=[])
        vehicle_description = VehicleDescriptionFactory(added_by=operateur.user, vehicle=vehicle)
        taxi = TaxiFactory(added_by=operateur.user, vehicle=vehicle)
        self._post_geotaxi(app, lon, lat, taxi, vehicle_description)
        # Operators can see their own taxis, but under an anonymous ID
        resp = operateur.client.get('/taxis?lon=%s&lat=%s' % (lon, lat))
        taxi = Taxi.query.one()  # refresh to access fake_taxi_id
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['id'] != taxi.id
        assert resp.json['data'][0]['id'] == taxi.fake_taxi_id
        assert resp.json['data'][0]['operator'] == 'chauffeur professionnel'  # No exception

    def test_ok_moteur_and_operateur_fake_taxi_id(self, app, moteur_and_operateur):
        app.config['FAKE_TAXI_ID'] = True
        ZUPCFactory()
        lon, lat = 2.35, 48.86
        vehicle = VehicleFactory(descriptions=[])
        vehicle_description = VehicleDescriptionFactory(added_by=moteur_and_operateur.user, vehicle=vehicle)
        taxi = TaxiFactory(added_by=moteur_and_operateur.user, vehicle=vehicle)
        self._post_geotaxi(app, lon, lat, taxi, vehicle_description)
        # Operators also moteurs can see their own taxis, but under an anonymous ID
        resp = moteur_and_operateur.client.get('/taxis?lon=%s&lat=%s' % (lon, lat))
        taxi = Taxi.query.one()  # refresh to access fake_taxi_id
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['id'] != taxi.id
        assert resp.json['data'][0]['id'] == taxi.fake_taxi_id
        assert resp.json['data'][0]['operator'] == 'chauffeur professionnel'  # No exception

    def test_ok_admin(self, app, admin):
        ZUPCFactory()  # Paris
        vehicle = VehicleFactory(descriptions=[])
        vehicle_description = VehicleDescriptionFactory(
            vehicle=vehicle,
            last_update_at=datetime.now(),
        )
        taxi = TaxiFactory(vehicle=vehicle, added_by=vehicle_description.added_by)
        operateur = vehicle_description.added_by.email

        lon, lat = 2.35, 48.86
        self._post_geotaxi(app, lon, lat, taxi, vehicle_description)

        # Admins can see the real operateur
        resp = admin.client.get('/taxis?lon=%s&lat=%s' % (lon, lat))
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['id'] == taxi.id
        assert resp.json['data'][0]['operator'] == operateur

    def test_radius(self, app, moteur):
        app.config['FAKE_TAXI_ID'] = False
        ZUPCFactory()
        now = datetime.now()
        TaxiFactory(
            vehicle__descriptions__radius=100, vehicle__descriptions__last_update_at=now
        )
        taxi_2 = TaxiFactory(
            vehicle__descriptions__radius=500, vehicle__descriptions__last_update_at=now
        )

        lon, lat = tmp_lon, tmp_lat = 2.35, 48.86
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
                # Move taxi a little bit further
                tmp_lon += 0.0001
                tmp_lat += 0.0001
                self._post_geotaxi(app, tmp_lon, tmp_lat, taxi, description)

        # The client is under 100 meters (~ 15.7 m)
        resp = moteur.client.get('/taxis?lon=%s&lat=%s' % (lon, lat))
        assert resp.status_code == 200
        assert len(resp.json['data']) == 2

        # The client is between 100 and 500 meters (~ 157 m)
        resp = moteur.client.get('/taxis?lon=%s&lat=%s' % (lon + 0.001, lat + 0.001))
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['id'] == taxi_2.id

        # The client is above 500 meters (~ 1.57 km)
        resp = moteur.client.get('/taxis?lon=%s&lat=%s' % (lon + 0.01, lat + 0.01))
        assert resp.status_code == 200
        assert len(resp.json['data']) == 0

    def test_exclusion(self, app, moteur, QueriesTracker):
        TownFactory(mulhouse=True)
        vehicle = VehicleFactory(descriptions=[])
        vehicle_description = VehicleDescriptionFactory(vehicle=vehicle)
        taxi = TaxiFactory(ads__insee='68224', vehicle=vehicle)
        ExclusionFactory()

        # Prefetch the exclusions
        helper = ExclusionHelper()
        helper.reset()

        # EuroAirport Bâle-Mulhouse-Fribourg
        lon, lat = 7.52637979704597, 47.5973205076925

        # Taxi is at the airport
        self._post_geotaxi(app, lon, lat, taxi, vehicle_description)

        # Client is at the airport too
        with QueriesTracker() as qtracker:
            resp = moteur.client.get(f'/taxis?lon={lon}&lat={lat}')
            # SELECT permissions
            assert qtracker.count == 1

        assert resp.status_code == 404, resp.json
        # No taxi should be returned.
        assert 'url' in resp.json['errors'], resp.json


class TestTaxiList:

    def test_invalid(self, anonymous, moteur, admin, operateur):
        resp = anonymous.client.get('/taxis/all')
        assert resp.status_code == 401

        for who in (moteur, admin):
            resp = who.client.get('/taxis/all')
            assert resp.status_code == 403

        # Invalid param
        resp = operateur.client.get('/taxis/all/?xxx=yyy')
        assert resp.status_code == 400

    def test_ok(self, operateur, QueriesTracker):
        # Two taxis belong to the operator.
        taxi_1 = TaxiFactory(added_by=operateur.user)
        TaxiFactory(added_by=operateur.user)
        # One taxi belongs to another user.
        taxi_other = TaxiFactory()

        with QueriesTracker() as qtracker:
            # SELECT role
            # SELECT taxis
            # SELECT COUNT (for pagination)
            resp = operateur.client.get('/taxis/all')
            assert qtracker.count == 3

        assert resp.status_code == 200
        assert len(resp.json['data']) == 2

        resp = operateur.client.get('/taxis/all?licence_plate=%s' % taxi_1.vehicle.licence_plate.lower())
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1

        resp = operateur.client.get('/taxis/all?id=%s' % taxi_1.id.lower())
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1

        resp = operateur.client.get('/taxis/all?id=%s' % taxi_other.id.lower())
        assert resp.status_code == 200
        assert len(resp.json['data']) == 0
