# -*- coding: utf-8 -*-
from .skeleton import Skeleton
from APITaxi.models.taxis import ADS, Vehicle
from APITaxi import db
from json import dumps, loads
from copy import deepcopy
from .fake_data import dict_ads, dict_vehicle
from APITaxi import index_zupc


class TestADSPost(Skeleton):
    url = '/ads/'
    role = 'operateur'

    def test_empty_post(self):
        r = self.post([])
        print r.json
        self.assert201(r)
        assert r.headers.get('Content-Type', None) == 'application/json'
        assert r.json['data'] == []

    def test_no_zupc(self):
        dict_ = dict_ads
        dict_['vehicle_id'] = None
        r = self.post([dict_])
        self.assert400(r)

    def test_simple(self):
        assert(index_zupc.size == 0)
        self.init_zupc()
        dict_ = dict_ads
        dict_['vehicle_id'] = None
        r = self.post([dict_])
        self.assert201(r)
        self.assertEqual(len(r.json['data']), 1)
        ads = r.json['data'][0]
        self.check_req_vs_dict(ads, dict_)
        self.assertEqual(len(ADS.query.all()), 1)
        assert(index_zupc.size == 1)

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

        self.assertEquals(len(ADS.query.all()), 1)
        self.assertEquals(len(Vehicle.query.all()), 1)

    def test_two_ads(self):
        self.init_zupc()
        dict_ = dict_ads
        dict_['vehicle_id'] = None
        r = self.post([dict_, dict_])
        self.assert201(r)
        self.assertEqual(len(r.json['data']), 2)
        self.assertEqual(len(ADS.query.all()), 2)

    def test_too_many_ads(self):
        dict_ = dict_ads
        r = self.post([dict_ for x in range(0, 251)])
        self.assertEqual(r.status_code, 413)
        self.assertEqual(len(ADS.query.all()), 0)

    def test_no_data(self):
        r = self.post({"d": None}, envelope_data=False)
        self.assert400(r)

    def test_bad_vehicle_id(self):
        dict_ = dict_ads
        dict_['vehicle_id'] = 1
        r = self.post([dict_])
        self.assert400(r)



