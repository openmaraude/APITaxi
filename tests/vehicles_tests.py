# -*- coding: utf-8 -*-
from .skeleton import Skeleton
from APITaxi_models.taxis import Vehicle, VehicleDescription
from json import loads
from .fake_data import dict_vehicle
from copy import deepcopy


class TestVehiclePost(Skeleton):
    url = '/vehicles/'
    role = 'operateur'

    def test_empty_post(self):
        r = self.post([])
        self.assert201(r)
        assert r.headers.get('Content-Type', None) == 'application/json'
        assert r.json['data'] == []

    def test_simple(self):
        dict_ = deepcopy(dict_vehicle)
        r = self.post([dict_])
        self.assert201(r)
        json = r.json
        self.assertEqual(len(json['data']), 1)
        vehicle = json['data'][0]
        self.check_req_vs_dict(vehicle, dict_)
        self.assertEqual(len(Vehicle.query.all()), 1)

    def test_same_vehicle_twice(self):
        dict_ = deepcopy(dict_vehicle)
        r = self.post([dict_, dict_])
        self.assert201(r)
        json = r.json
        self.assertEqual(len(json['data']), 2)
        self.assertEqual(len(Vehicle.query.all()), 1)

    def test_same_vehicle_twice_two_requests(self):
        dict_ = deepcopy(dict_vehicle)
        r = self.post([dict_])
        self.assert201(r)
        json = r.json
        self.assertEqual(len(json['data']), 1)
        self.assertEqual(len(Vehicle.query.all()), 1)
        r = self.post([dict_])
        self.assert201(r)
        json = r.json
        self.assertEqual(len(json['data']), 1)
        self.assertEqual(len(Vehicle.query.all()), 1)

    def test_too_many_vehicles(self):
        dict_ = deepcopy(dict_vehicle)
        r = self.post([dict_ for x in range(0, 251)])
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(Vehicle.query.all()), 0)

    def test_no_data(self):
        r = self.post({"d": None}, envelope_data=False)
        self.assert400(r)

    def test_with_id(self):
        dict_ = deepcopy(dict_vehicle)
        dict_['id'] = 0
        r = self.post([dict_])
        self.assert201(r)
        json = r.json
        self.assertEqual(len(json['data']), 1)
        vehicle = json['data'][0]
        del dict_['id']
        self.check_req_vs_dict(vehicle, dict_)
        self.assertEqual(len(Vehicle.query.all()), 1)
        dict_ = deepcopy(dict_vehicle)
        dict_['id'] = 'aa'
        r = self.post([dict_])
        self.assert201(r)
        json = r.json
        self.assertEqual(len(json['data']), 1)
        vehicle = json['data'][0]
        del dict_['id']
        self.check_req_vs_dict(vehicle, dict_)
        self.assertEqual(len(Vehicle.query.all()), 1)

    def test_change_wifi(self):
        dict_ = deepcopy(dict_vehicle)
        r = self.post([dict_])
        self.assert201(r)
        json = r.json
        self.assertEqual(len(json['data']), 1)
        self.assertEqual(len(Vehicle.query.all()), 1)
        dict_['wifi'] = not dict_['wifi']
        r = self.post([dict_])
        self.assert201(r)
        json = r.json
        self.assertEqual(len(json['data']), 1)
        self.assertEqual(len(Vehicle.query.all()), 1)
        self.assertEqual(len(VehicleDescription.query.all()), 1)
        self.assertEqual(VehicleDescription.query.first().wifi, dict_['wifi'])

    def test_bad_date(self):
        dict_ = deepcopy(dict_vehicle)
        dict_['date_dernier_ct'] = 'bad'
        r = self.post([dict_])
        self.assert400(r)
        dict_ = deepcopy(dict_vehicle)
        dict_['date_validite_ct'] = 'bad'
        r = self.post([dict_])
        self.assert400(r)
