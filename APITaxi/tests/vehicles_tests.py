from .skeleton import Skeleton
from APITaxi.models.taxis import Vehicle
from APITaxi.models.administrative import Departement
from json import dumps, loads
from copy import deepcopy
from APITaxi import db
from .fake_data import dict_vehicle


class TestVehiclePost(Skeleton):
    url = '/vehicles/'

    def test_empty_post(self):
        r = self.post([])
        self.assert200(r)
        assert r.headers.get('Content-Type', None) == 'application/json'
        json = loads(r.data)
        assert json['data'] == []

    def test_simple(self):
        dict_ = dict_vehicle
        r = self.post([dict_])
        self.assert200(r)
        json = loads(r.data)
        self.assertEqual(len(json['data']), 1)
        vehicle = json['data'][0]
        self.check_req_vs_dict(vehicle, dict_)
        self.assertEqual(len(Vehicle.query.all()), 1)

    def test_two_vehicles(self):
        dict_ = dict_vehicle
        r = self.post([dict_, dict_])
        self.assert200(r)
        json = loads(r.data)
        self.assertEqual(len(json['data']), 2)
        self.assertEqual(len(Vehicle.query.all()), 2)

    def test_too_many_vehicles(self):
        dict_ = dict_vehicle
        r = self.post([dict_ for x in xrange(0, 251)])
        self.assertEqual(r.status_code, 413)
        self.assertEqual(len(Vehicle.query.all()), 0)

    def test_no_data(self):
        r = self.post({"d": None}, envelope_data=False)
        self.assert400(r)

