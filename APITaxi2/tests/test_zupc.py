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
            'stats': {
                'total': 0
            },
        }]}

        zupc = ZUPCFactory()
        ZUPCFactory(bordeaux=True)  # Shouldn't appear in the results

        with QueriesTracker() as qtracker:
            resp = moteur.client.get('zupc?lon=2.35&lat=48.86')
            # List permissions, List Town, List ZUPC
            assert qtracker.count == 3

        assert resp.status_code == 200
        assert resp.json['data'] == [{
            'type': 'ZUPC',
            'name': zupc.nom,
            'zupc_id': zupc.zupc_id,
            'stats': {
                'total': 0,
            },
        }]

        resp = operateur.client.get('zupc?lon=2.35&lat=48.86')
        assert resp.status_code == 200
        assert resp.json['data'] == [{
            'type': 'ZUPC',
            'name': zupc.nom,
            'zupc_id': zupc.zupc_id,
            'stats': {
                'total': 0,
                'operators': {
                    operateur.user.email: 0,
                }
            },
        }]
