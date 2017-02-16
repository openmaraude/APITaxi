# -*- coding: utf-8 -*-
from .skeleton import Skeleton
import APITaxi_models as models
from json import dumps, loads
from copy import deepcopy
from .fake_data import dict_ads, dict_vehicle


class TestADSPost(Skeleton):
    url = '/ads/'
    role = 'operateur'

    def test_empty_post(self):
        r = self.post([])
        self.assert201(r)
        assert r.headers.get('Content-Type', None) == 'application/json'
        assert r.json['data'] == []

    def test_no_vehicle(self):
        dict_ = deepcopy(dict_ads)
        dict_['vehicle_id'] = None
        r = self.post([dict_])
        self.assert400(r)

    def test_simple(self):
        self.init_zupc()
        dict_ = deepcopy(dict_ads)
        dict_['vehicle_id'] = None
        r = self.post([dict_])
        self.assert201(r)
        self.assertEqual(len(r.json['data']), 1)
        ads = r.json['data'][0]
        self.check_req_vs_dict(ads, dict_)
        list_ads = models.ADS.query.all()
        self.assertEqual(len(list_ads), 1)
        assert all(map(lambda ads: ads.zupc_id is not None, list_ads))

    def test_vehicle(self):
        self.init_zupc()
        dict_v = deepcopy(dict_vehicle)
        r = self.post([dict_v], url='/vehicles/')
        self.assert201(r)
        vehicle = r.json['data'][0]
        self.check_req_vs_dict(vehicle, dict_v)
        vehicle_id = vehicle['id']

        dict_a = deepcopy(dict_ads)
        dict_a['vehicle_id'] = vehicle_id
        r = self.post([dict_a])
        self.assert201(r)
        ads = r.json['data'][0]
        self.check_req_vs_dict(ads, dict_a)

        list_ads = models.ADS.query.all()
        self.assertEqual(len(list_ads), 1)
        assert all(map(lambda ads: ads.zupc_id is not None, list_ads))
        self.assertEquals(len(models.Vehicle.query.all()), 1)

    def test_two_ads(self):
        self.init_zupc()
        dict_ = deepcopy(dict_ads)
        dict_['vehicle_id'] = None
        r = self.post([dict_, dict_])
        self.assert201(r)
        self.assertEqual(len(r.json['data']), 2)
        list_ads = models.ADS.query.all()
        self.assertEqual(len(list_ads), 2)
        assert all(map(lambda ads: ads.zupc_id is not None, list_ads))

    def test_too_many_ads(self):
        dict_ = deepcopy(dict_ads)
        r = self.post([dict_ for x in range(0, 251)])
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(models.ADS.query.all()), 0)

    def test_no_data(self):
        r = self.post({"d": None}, envelope_data=False)
        self.assert400(r)

    def test_bad_vehicle_id(self):
        dict_ = deepcopy(dict_ads)
        dict_['vehicle_id'] = 1
        r = self.post([dict_])
        self.assert400(r)

    def test_vehicle_id_O(self):
        self.init_zupc()
        dict_ = deepcopy(dict_ads)
        dict_['vehicle_id'] = 0
        r = self.post([dict_])
        self.assert201(r)

    def test_no_vehicle_id(self):
        self.init_zupc()
        dict_ = deepcopy(dict_ads)
        r = self.post([dict_])
        self.assert201(r)

    def test_bad_owner_type(self):
        self.init_zupc()
        dict_ = deepcopy(dict_ads)
        dict_['vehicle_id'] = None
        dict_['owner_type'] = 'string'
        r = self.post([dict_])
        self.assert400(r)
        assert 'data.0.owner_type' in r.json['errors']

    def test_no_owner_type(self):
        self.init_zupc()
        dict_ = deepcopy(dict_ads)
        dict_['vehicle_id'] = None
        dict_['owner_type'] = None
        r = self.post([dict_])
        self.assert400(r)
        assert "data.0.owner_type" in r.json['errors']

