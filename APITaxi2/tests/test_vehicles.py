from sqlalchemy.orm import joinedload

from APITaxi_models2 import (
    Vehicle,
    VehicleConstructor,
    VehicleDescription,
    VehicleModel,
)


class TestVehiclePost:
    def test_invalid(self, anonymous, moteur, operateur):
        # Login required
        resp = anonymous.client.post('/vehicles', json={})
        assert resp.status_code == 401

        resp = moteur.client.post('/vehicles', json={})
        assert resp.status_code == 403

        resp = operateur.client.post('/vehicles', json={'data': [{}]})
        assert resp.status_code == 400
        # The only required key is "licence_plate"
        assert list(resp.json['errors']['data']['0'].keys()) == ['licence_plate']

    def test_ok(self, operateur, admin, QueriesTracker):
        with QueriesTracker() as qtracker:
            resp = operateur.client.post('/vehicles', json={
                'data': [{
                    'licence_plate': 'licence1',
                    'internal_id': 'internal_id',
                    'model_year': 1938,
                    'engine': 'v12',
                    'horse_power': 42.2,
                    'relais': False,
                    'horodateur': 'horodateur',
                    'taximetre': 'taximetre',
                    'date_dernier_ct': '2012-12-21',
                    'date_validite_ct': '2013-12-21',
                    'special_need_vehicle': True,
                    'type_': 'normal',
                    'luxury': True,
                    'credit_card_accepted': True,
                    'nfc_cc_accepted': True,
                    'amex_accepted': True,
                    'bank_check_accepted': True,
                    'fresh_drink': True,
                    'dvd_player': True,
                    'tablet': True,
                    'wifi': True,
                    'baby_seat': True,
                    'bike_accepted': True,
                    'pet_accepted': True,
                    'air_con': True,
                    'electronic_toll': True,
                    'gps': True,
                    'cpam_conventionne': True,
                    'every_destination': True,
                    'color': 'blue',
                    'nb_seats': 18,
                    'model': 'mymodel',
                    'constructor': 'myconstructor',
                }]
            })
            # SELECT permissions
            # SELECT vehicle, INSERT vehicle
            # SELECT vehicle_description
            # SELECT model, INSERT model
            # SELECT constructor, INSERT constructor
            # INSERT vehicle_description
            assert qtracker.count == 9

        assert resp.status_code == 200
        assert Vehicle.query.count() == 1
        assert VehicleConstructor.query.count() == 1
        assert VehicleDescription.query.count() == 1
        assert VehicleModel.query.count() == 1
        vehicle = Vehicle.query.one()
        assert resp.json == {'data': [{
            'id': vehicle.id,
            'air_con': True,
            'amex_accepted': True,
            'baby_seat': True,
            'bank_check_accepted': True,
            'bike_accepted': True,
            'color': 'blue',
            'constructor': 'myconstructor',
            'cpam_conventionne': True,
            'credit_card_accepted': True,
            'date_dernier_ct': 'Fri, 21 Dec 2012 00:00:00 GMT',
            'date_validite_ct': 'Sat, 21 Dec 2013 00:00:00 GMT',
            'dvd_player': True,
            'electronic_toll': True,
            'engine': 'v12',
            'every_destination': True,
            'fresh_drink': True,
            'gps': True,
            'horodateur': 'horodateur',
            'horse_power': 42.2,
            'internal_id': 'internal_id',
            'licence_plate': 'licence1',
            'luxury': True,
            'model': 'mymodel',
            'model_year': 1938,
            'nb_seats': 18,
            'nfc_cc_accepted': True,
            'pet_accepted': True,
            'relais': False,
            'special_need_vehicle': True,
            'tablet': True,
            'taximetre': 'taximetre',
            'type_': 'normal',
            'wifi': True
        }]}

        # If we make a query with the same user to create the same vehicle
        # (identified by licence_plate), the same object is returned.
        resp = operateur.client.post('/vehicles', json={
            'data': [{
                'licence_plate': 'licence1'
            }]
        })
        assert resp.status_code == 200
        assert Vehicle.query.count() == 1
        assert VehicleDescription.query.count() == 1

        # Same query with different user: vehicle is returned, but
        # VehicleDescription is created.
        resp = admin.client.post('/vehicles', json={
            'data': [{
                'licence_plate': 'licence1'
            }]
        })
        assert resp.status_code == 200
        assert Vehicle.query.count() == 1
        assert VehicleDescription.query.count() == 2

        # "model" and "constructor" are stored in separate tables. It is
        # possible to create a vehicle with these fields null.
        resp = operateur.client.post('/vehicles', json={
            'data': [{
                'licence_plate': 'licence2'
            }]
        })
        assert resp.status_code == 200
        vehicle = Vehicle.query.options(
            joinedload(Vehicle.descriptions).joinedload(VehicleDescription.model)
        ).options(
            joinedload(Vehicle.descriptions).joinedload(VehicleDescription.constructor)
        ).filter_by(licence_plate='licence2').one()
        assert vehicle.descriptions
        assert vehicle.descriptions[0].model is None
        assert vehicle.descriptions[0].constructor is None
