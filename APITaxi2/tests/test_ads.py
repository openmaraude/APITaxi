from APITaxi_models2 import ADS
from APITaxi_models2.unittest.factories import (
    ADSFactory,
    VehicleFactory,
    ZUPCFactory
)


class TestADSCreate:
    def test_invalid(self, anonymous, moteur, operateur):
        # Login required
        resp = anonymous.client.post('/ads', json={})
        assert resp.status_code == 401

        # Permission denied
        resp = moteur.client.post('/ads', json={})
        assert resp.status_code == 403

        # Permissions OK, check required fields
        resp = operateur.client.post('/ads', json={'data': [{
        }]})
        assert resp.status_code == 400
        assert 'category' in resp.json['errors']['data']['0']
        assert 'insee' in resp.json['errors']['data']['0']
        assert 'numero' in resp.json['errors']['data']['0']
        assert 'owner_name' in resp.json['errors']['data']['0']
        assert 'owner_type' in resp.json['errors']['data']['0']

        # Data OK, but invalid vehicle id
        resp = operateur.client.post('/ads', json={'data': [{
            'numero': '1234567',
            'doublage': True,
            'insee': '75101',
            'owner_type': 'individual',
            'owner_name': 'Roger Federer',
            'category': 'INCESSIBLE',
            'vehicle_id': 1337
        }]})
        assert resp.status_code == 404
        assert len(resp.json['errors']['data']['0']['vehicle_id']) > 0

        # Non-existing INSEE code
        resp = operateur.client.post('/ads', json={'data': [{
            'numero': '1234567',
            'doublage': True,
            'insee': '9999999',
            'owner_type': 'individual',
            'owner_name': 'Roger Federer',
            'category': 'INCESSIBLE',
        }]})
        assert resp.status_code == 404
        assert len(resp.json['errors']['data']['0']['insee']) > 0

    def test_already_exists(self, operateur):
        """If ADS already exists, the existing item is updated and returned."""
        assert ADS.query.count() == 0
        ads = ADSFactory()

        resp = operateur.client.post('/ads', json={'data': [{
            # Fields used to retrieve the existing ADS
            'numero': ads.numero,
            'insee': ads.insee,
            # Fields to update
            'doublage': False,
            'owner_type': 'company',
            'owner_name': 'Roger Federer',
            'category': 'NEW_CATEGORY',
        }]})
        assert resp.status_code == 200
        assert ADS.query.count() == 1

    def test_ok(self, operateur, QueriesTracker):
        vehicle = VehicleFactory()
        zupc = ZUPCFactory()

        with QueriesTracker() as qtracker:
            resp = operateur.client.post('/ads', json={'data': [{
                'numero': '1337',
                'insee': zupc.insee,
                'doublage': True,
                'owner_type': 'individual',
                'owner_name': 'Roger Federer',
                'category': 'category',
                'vehicle_id': vehicle.id
            }]})
            # SELECT permissions, SELECT vehicle, SELECT ZUPC corresponding to
            # insee, SELECT existing ADS, INSERT ADS
            assert qtracker.count == 5

        assert resp.status_code == 201
        assert resp.json['data'][0]['numero'] == '1337'
        assert resp.json['data'][0]['insee'] == zupc.insee
        assert resp.json['data'][0]['doublage'] is True
        assert resp.json['data'][0]['owner_type'] == 'individual'
        assert resp.json['data'][0]['owner_name'] == 'Roger Federer'
        assert resp.json['data'][0]['category'] == 'category'
        assert resp.json['data'][0]['vehicle_id'] == vehicle.id

        assert ADS.query.count() == 1
