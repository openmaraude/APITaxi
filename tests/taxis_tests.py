from .skeleton import Skeleton
from APITaxi.models.taxis import Taxi
from APITaxi.models.administrative import Departement
from json import dumps, loads
from copy import deepcopy
from .fake_data import dict_vehicle, dict_ads, dict_driver, dict_taxi
from APITaxi import redis_store
import time

class TestTaxiGet(Skeleton):
    url = '/taxis/'
    role = 'operateur'

    def add(self):
        self.init_dep()
        self.post([dict_driver], url='/drivers/')
        r = self.post([dict_vehicle], url='/vehicles/')
        self.assert201(r)
        vehicle_id = r.json['data'][0]['id']
        dict_ads_ = deepcopy(dict_ads)
        dict_ads_['vehicle_id'] = vehicle_id
        self.post([dict_ads_], url='/ads/')
        r = self.post([dict_taxi])
        id_taxi = r.json['data'][0]['id']
        redis_store.hset('taxi:{}'.format(id_taxi), 'user_operateur',
                Taxi._FORMAT_OPERATOR.format(timestamp=int(time.time()),
                    lat=2, lon=49, status='free', device='mobile'))
        return id_taxi

    def test_get_taxi(self):
        id_taxi = self.add()
        r = self.get('/taxis/{}/'.format(id_taxi))
        self.assert200(r)
        assert(len(r.json['data']) == 1)
        assert('nb_seats' in r.json['data'][0]['vehicle'])

    def test_get_taxi_other_op(self):
        id_taxi = self.add()
        r = self.get('/taxis/{}/'.format(id_taxi), user='user_operateur_2')
        self.assert403(r)


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

    def test_missing_departement_in_db(self):
        r = self.post([dict_taxi])
        self.assert404(r)

    def test_missing_driver_in_db(self):
        self.init_dep()
        r = self.post([dict_taxi])
        self.assert404(r)

    def test_missing_vehicle_in_db(self):
        self.init_dep()
        self.post([dict_driver], url='/drivers/')
        r = self.post([dict_taxi])
        self.assert404(r)

    def test_missing_ads_in_db(self):
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
        vehicle_id = r.json['data'][0]['id']
        dict_ads_ = deepcopy(dict_ads)
        dict_ads_['vehicle_id'] = vehicle_id
        self.post([dict_ads_], url='/ads/')
        r = self.post([dict_taxi])
        self.assert201(r)
        self.check_req_vs_dict(r.json['data'][0], dict_taxi)
        self.assertEqual(len(Taxi.query.all()), 1)

    def test_missing_ads_field(self):
        self.init_dep()
        self.post([dict_driver], url='/drivers/')
        r = self.post([dict_vehicle], url='/vehicles/')
        self.assert201(r)
        vehicle_id = r.json['data'][0]['id']
        dict_ads_ = deepcopy(dict_ads)
        dict_ads_['vehicle_id'] = vehicle_id
        self.post([dict_ads_], url='/ads/')
        dict_taxi_d = deepcopy(dict_taxi)
        del dict_taxi_d['ads']
        r = self.post([dict_taxi_d])
        self.assert400(r)

    def test_missing_driver_field(self):
        self.init_dep()
        self.post([dict_driver], url='/drivers/')
        r = self.post([dict_vehicle], url='/vehicles/')
        self.assert201(r)
        vehicle_id = r.json['data'][0]['id']
        dict_ads_ = deepcopy(dict_ads)
        dict_ads_['vehicle_id'] = vehicle_id
        self.post([dict_ads_], url='/ads/')
        dict_taxi_d = deepcopy(dict_taxi)
        del dict_taxi_d['driver']
        r = self.post([dict_taxi_d])
        self.assert400(r)

    def test_missing_vehicle_field(self):
        self.init_dep()
        self.post([dict_driver], url='/drivers/')
        r = self.post([dict_vehicle], url='/vehicles/')
        self.assert201(r)
        vehicle_id = r.json['data'][0]['id']
        dict_ads_ = deepcopy(dict_ads)
        dict_ads_['vehicle_id'] = vehicle_id
        self.post([dict_ads_], url='/ads/')
        dict_taxi_d = deepcopy(dict_taxi)
        del dict_taxi_d['vehicle']
        r = self.post([dict_taxi_d])
        self.assert400(r)

    def test_bad_ads_field(self):
        self.init_dep()
        self.post([dict_driver], url='/drivers/')
        r = self.post([dict_vehicle], url='/vehicles/')
        self.assert201(r)
        vehicle_id = r.json['data'][0]['id']
        dict_ads_ = deepcopy(dict_ads)
        dict_ads_['vehicle_id'] = vehicle_id
        self.post([dict_ads_], url='/ads/')
        dict_taxi_d = deepcopy(dict_taxi)
        dict_taxi_d['ads']['numero'] = '2'
        r = self.post([dict_taxi_d])
        self.assert404(r)

    def test_bad_driver_field(self):
        self.init_dep()
        self.post([dict_driver], url='/drivers/')
        r = self.post([dict_vehicle], url='/vehicles/')
        self.assert201(r)
        vehicle_id = r.json['data'][0]['id']
        dict_ads_ = deepcopy(dict_ads)
        dict_ads_['vehicle_id'] = vehicle_id
        self.post([dict_ads_], url='/ads/')
        dict_taxi_d = deepcopy(dict_taxi)
        dict_taxi_d['driver']['professional_licence'] = 'bad'
        r = self.post([dict_taxi_d])
        self.assert404(r)

    def test_bad_vehicle_field(self):
        self.init_dep()
        self.post([dict_driver], url='/drivers/')
        r = self.post([dict_vehicle], url='/vehicles/')
        self.assert201(r)
        vehicle_id = r.json['data'][0]['id']
        dict_ads_ = deepcopy(dict_ads)
        dict_ads_['vehicle_id'] = vehicle_id
        self.post([dict_ads_], url='/ads/')
        dict_taxi_d = deepcopy(dict_taxi)
        dict_taxi_d['vehicle']['licence_plate'] = 'bad'
        r = self.post([dict_taxi_d])
        self.assert404(r)
