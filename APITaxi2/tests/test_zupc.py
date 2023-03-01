from APITaxi_models2.unittest.factories import (
    TownFactory,
    ZUPCFactory,
)


class TestZUPCList:
    def test_invalid(self, anonymous, moteur, operateur):
        # Required querystring arguments ?lon and ?lat are not provided
        resp = operateur.client.get('/zupc')
        assert resp.status_code == 400
        assert 'lon' in resp.json['errors']
        assert 'lat' in resp.json['errors']

        resp = anonymous.client.get('/zupc?lon=2.35&lat=48.86')
        assert resp.status_code == 401

    def test_ok(self, operateur, moteur, QueriesTracker):
        TownFactory()

        # lon=2.35&lat=48.86 = location in middle of Paris. No ZUPC is created
        # yet, so the result is empty.
        resp = moteur.client.get('zupc?lon=2.35&lat=48.86')
        assert resp.status_code == 200
        # A ZUPC is simulated at the town level
        assert resp.json == {'data': [{
            'type': 'city',
            'name': 'Paris',
            'insee': '75056',
            'stats': {},
        }]}

        zupc = ZUPCFactory()
        ZUPCFactory(bordeaux=True)  # Shouldn't appear in the results

        with QueriesTracker() as qtracker:
            resp = moteur.client.get('zupc?lon=2.35&lat=48.86')
            # SELECT permissions, SELECT town, SELECT ZUPC
            assert qtracker.count == 3

        assert resp.status_code == 200
        assert resp.json['data'] == [{
            'type': 'ZUPC',
            'name': zupc.nom,
            'zupc_id': zupc.zupc_id,
            'stats': {},
        }]

        resp = operateur.client.get('zupc?lon=2.35&lat=48.86')
        assert resp.status_code == 200
        assert resp.json['data'] == [{
            'type': 'ZUPC',
            'name': zupc.nom,
            'zupc_id': zupc.zupc_id,
            'stats': {
                'operators': {
                    operateur.user.email: 0,
                }
            },
        }]


class TestZUPCLive:
    def test_invalid(self, anonymous):
        resp = anonymous.client.get('/zupc/live')
        assert resp.status_code == 401

    def test_ok(self, operateur, QueriesTracker):
        zupc = ZUPCFactory()
        zupc2 = ZUPCFactory(bordeaux=True)

        with QueriesTracker() as qtracker:
            resp = operateur.client.get('/zupc/live')
            # SELECT permissions, SELECT zupc, total active taxis, operator's active taxis
            assert qtracker.count == 4

        assert resp.status_code == 200
        assert len(resp.json['data']) == 2
        assert resp.json['data'][0]['id'] in (zupc.zupc_id, zupc2.zupc_id)
        assert resp.json['data'][0]['nom'] in (zupc.nom, zupc2.nom)
        assert resp.json['data'][0]['stats'] == {
            'operators': {
                operateur.user.email: 0
            }
        }


class TestTownList:
    def test_anonymous(self, anonymous):
        resp = anonymous.client.get('/towns')
        assert resp.status_code == 401

    def test_ok(self, operateur, moteur, QueriesTracker):
        ZUPCFactory()
        ZUPCFactory(bordeaux=True)

        with QueriesTracker() as qtracker:
            resp = operateur.client.get('/towns')
            # SELECT permissions, SELECT towns
            assert qtracker.count == 2

        assert resp.status_code == 200
        assert len(resp.json['data']) == 3
        assert resp.json['data'][0]['insee'] == '33063'
        assert resp.json['data'][0]['name'] == 'Bordeaux'

        # This endpoint is not restricted to operateurs, quickly check moteurs
        assert moteur.client.get('/towns').status_code == 200
