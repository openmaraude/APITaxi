# -*- coding: utf-8 -*-
from .skeleton import Skeleton
from APITaxi.models.taxis import ADS, Vehicle
from APITaxi.extensions import db, index_zupc
from json import dumps, loads
from copy import deepcopy
from .fake_data import dict_ads, dict_vehicle


class TestZUPCSearch(Skeleton):
    url = '/zupc/'
    role = 'operateur'

    def test_nominative_case(self):
        taxi = self.post_taxi_and_locate(lat=2.3, lon=48.5, float_=False)
        self.init_zupc()
        r = self.get('/zupc/?lat=2.3&lon=48.7')
        self.assert200(r)
        r_json = r.json
        assert 'data' in r_json
        assert len(r_json['data']) == 1
        zupc = r_json['data'][0]
        for k in ['active', 'nom', 'insee']:
            assert k in zupc

    def test_no_argument(self):
        taxi = self.post_taxi_and_locate(lat=2.3, lon=48.5, float_=False)
        self.init_zupc()
        r = self.get('/zupc/')
        self.assert400(r)

    def test_bad_type(self):
        taxi = self.post_taxi_and_locate(lat=2.3, lon=48.5, float_=False)
        self.init_zupc()
        r = self.get('/zupc/?lat=a&lon=2.3')
        self.assert400(r)
        r = self.get('/zupc/?lon=2.3&lat=a')
        self.assert400(r)
