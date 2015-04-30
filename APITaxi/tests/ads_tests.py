from .skeleton import Skeleton
from APITaxi.models.taxis import ADS, Vehicle
from json import dumps, loads
from copy import deepcopy


class TestADSPost(Skeleton):
    dict_ads = {
        "category": "c1",
        "doublage": True,
        "insee": "75000",
        "numero": "1",
        "owner_name": "name",
        "owner_type": "company",
    }

    dict_vehicle = {
        "licence_plate" : "DF-118-FG",
        "model" : "BX",
        "model_year" : 1995,
        "engine" : "GO",
        "horse_power" : 2.0,
        "type_" : "sedan",
        "relais" : False,
        "constructor" : "Citroen",
        "horodateur" : "aa",
        "taximetre" : "aa",
        "date_dernier_ct" : "2015-03-03",
        "date_validite_ct" : "2016-03-03",
        "luxury" : False,
        "credit_card_accepted" : True,
        "nfc_cc_accepted" : False,
        "amex_accepted" : False,
        "bank_check_accepted" : False,
        "fresh_drink" : True,
        "dvd_player" : False,
        "tablet" : True,
        "wifi" : True,
        "baby_seat" : False,
        "bike_accepted" : False,
        "pet_accepted" : True,
        "air_con" : True,
        "electronic_toll" : False,
        "gps" : True,
        "cpam_conventionne" : False,
        "every_destination" : False,
        "color" : "grey",
        "special_need_vehicle" : True,
        }

    def post(self, data, url='/ads/', envelope_data=True):
        if envelope_data:
            data = {"data": data}
        return self.client.post(url, data=dumps(data),
                                follow_redirects=True,
                                headers={
                                    "Content-Type": "application/json",
                                    "Authorization": "user_operateur:operateur"
                                })

    def test_empty_post(self):
        r = self.post([])
        self.assert200(r)
        assert r.headers.get('Content-Type', None) == 'application/json'
        json = loads(r.data)
        assert json['data'] == []

    def test_simple(self):
        dict_ = self.__class__.dict_ads
        dict_['vehicle_id'] = None
        r = self.post([dict_])
        self.assert200(r)
        json = loads(r.data)
        self.assertEqual(len(json['data']), 1)
        ads = json['data'][0]
        self.check_req_vs_dict(ads, dict_)
        self.assertEqual(len(ADS.query.all()), 1)

    def test_vehicle(self):
        dict_vehicle = deepcopy(self.__class__.dict_vehicle)
        r = self.post([dict_vehicle], url='/vehicles/')
        self.assert200(r)
        json = loads(r.data)
        vehicle = json['data'][0]
        self.check_req_vs_dict(vehicle, dict_vehicle)
        vehicle_id = vehicle['id']

        dict_ads = deepcopy(self.__class__.dict_ads)
        dict_ads['vehicle_id'] = vehicle_id
        r = self.post([dict_ads])
        self.assert200(r)
        json = loads(r.data)
        ads = json['data'][0]
        self.check_req_vs_dict(ads, dict_ads)

        self.assertEquals(len(ADS.query.all()), 1)
        self.assertEquals(len(Vehicle.query.all()), 1)

    def test_two_ads(self):
        dict_ = self.__class__.dict_ads
        dict_['vehicle_id'] = None
        r = self.post([dict_, dict_])
        self.assert200(r)
        json = loads(r.data)
        self.assertEqual(len(json['data']), 2)
        self.assertEqual(len(ADS.query.all()), 2)

    def test_too_many_ads(self):
        dict_ = self.__class__.dict_ads
        r = self.post([dict_ for x in xrange(0, 251)])
        self.assertEqual(r.status_code, 413)
        self.assertEqual(len(ADS.query.all()), 0)

    def test_no_data(self):
        r = self.post({"d": None}, envelope_data=False)
        self.assert400(r)

    def test_bad_vehicle_id(self):
        dict_ = self.__class__.dict_ads
        dict_['vehicle_id'] = 1
        r = self.post([dict_])
        self.assert400(r)



