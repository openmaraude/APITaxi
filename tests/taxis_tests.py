from .skeleton import Skeleton
from APITaxi.models.taxis import Taxi
from APITaxi.models.administrative import Departement
from json import dumps, loads
from copy import deepcopy
from .fake_data import dict_vehicle, dict_ads, dict_driver, dict_taxi


class TestTaxiPost(Skeleton):
    url = '/taxis/'
    role = 'operateur'

    def test_no_data(self):
        r = self.post({}, envelope_data=False)
        self.assert400(r)

    def test_too_many(self):
        r = self.post([{}, {}])
        self.assertEqual(r.status_code, 413)

    def test_missing_fields(self):
        dict_ = {
            'vehicle': None,
            'driver': {'professional_licence': 'a', 'deparement': '53'}
        }
        r = self.post([dict_])
        self.assert400(r)

    def test_missing_departement(self):
        r = self.post([dict_taxi])
        self.assert404(r)

    def test_missing_driver(self):
        self.init_dep()
        r = self.post([dict_taxi])
        self.assert404(r)

    def test_missing_vehicle(self):
        self.init_dep()
        self.post([dict_driver], url='/drivers/')
        r = self.post([dict_taxi])
        self.assert404(r)

    def test_missing_ads(self):
        self.init_dep()
        self.post([dict_driver], url='/drivers/')
        self.post([dict_vehicle], url='/vehicles/')
        r = self.post([dict_taxi])
        self.assert404(r)

    def test_add_taxi(self):
        self.init_dep()
        self.post([dict_driver], url='/drivers/')
        r = self.post([dict_vehicle], url='/vehicles/')
        self.assert201(r)
        vehicle_id = loads(r.data)['data'][0]['id']
        dict_ads_ = deepcopy(dict_ads)
        dict_ads_['vehicle_id'] = vehicle_id
        self.post([dict_ads_], url='/ads/')
        r = self.post([dict_taxi])
        self.assert201(r)
        json = loads(r.data)
        self.check_req_vs_dict(json['data'][0], dict_taxi)
        self.assertEqual(len(Taxi.query.all()), 1)


