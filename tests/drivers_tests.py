# -*- coding: utf-8 -*-
from .skeleton import Skeleton
from .fake_data import dict_driver
from APITaxi.models.taxis import Driver
from json import dumps, loads
from copy import deepcopy
from APITaxi.extensions import db


class TestDriverPost(Skeleton):
    url = '/drivers/'
    role = 'operateur'


    def test_null(self):
        r = self.post([])
        self.assert201(r)

    def test_simple(self):
        self.init_dep()
        dict_ = deepcopy(dict_driver)
        r = self.post([dict_])
        self.assert201(r)
        self.check_req_vs_dict(r.json['data'][0], dict_)
        self.assertEqual(len(Driver.query.all()), 1)

    def test_no_data(self):
        self.init_dep()
        r = self.post({}, envelope_data=False)
        self.assert400(r)
        self.assertEqual(len(Driver.query.all()), 0)

    def test_too_many_drivers(self):
        self.init_dep()
        r = self.post([dict_driver for x in range(0, 251)])
        self.assertEqual(r.status_code, 413)
        self.assertEqual(len(Driver.query.all()), 0)

    def test_no_departement(self):
        r = self.post([dict_driver])
        self.assert404(r)
        self.assertEqual(len(Driver.query.all()), 0)

    def test_pas_de_nom(self):
        dict_ = deepcopy(dict_driver)
        del dict_['first_name']
        r = self.post([dict_])
        self.assert404(r)
        self.assertEqual(len(Driver.query.all()), 0)

    def test_two_inserts(self):
        self.init_dep()
        r = self.post([dict_driver for x in range(0, 2)])
        self.assert201(r)
        self.assertEqual(len(Driver.query.all()), 2)

    def test_one_language(self):
        self.init_dep()
        d = deepcopy(dict_driver)
        d['languages'] = ['fr']
        r = self.post([d])
        self.assert201(r)
        self.assertEqual(len(Driver.query.all()), 1)
        driver = r.json['data'][0]
        assert 'languages' in driver.keys()
        assert isinstance(driver['languages'], list)
        assert len(driver['languages']) == 1
        assert driver['languages'][0] == 'fr'

    def test_one_invalid_language(self):
        self.init_dep()
        d = deepcopy(dict_driver)
        d['languages'] = ['zz']
        r = self.post([d])
        self.assert400(r)
        error = r.json
        assert(error['message'][:2] == 'zz')

    def test_string_languages(self):
        self.init_dep()
        d = deepcopy(dict_driver)
        d['languages'] = 'zz'
        r = self.post([d])
        self.assert400(r)
        error = r.json

    def test_two_languages(self):
        self.init_dep()
        d = deepcopy(dict_driver)
        d['languages'] = ['fr', 'en']
        r = self.post([d])
        self.assert201(r)
        self.assertEqual(len(Driver.query.all()), 1)
        driver = r.json['data'][0]
        assert 'languages' in driver.keys()
        assert isinstance(driver['languages'], list)
        assert len(driver['languages']) == 2
        assert 'fr' in driver['languages']
        assert 'en' in driver['languages']

    def test_same_language_twice(self):
        self.init_dep()
        d = deepcopy(dict_driver)
        d['languages'] = ['fr', 'fr']
        r = self.post([d])
        self.assert201(r)
        self.assertEqual(len(Driver.query.all()), 1)
        driver = r.json['data'][0]
        assert 'languages' in driver.keys()
        assert isinstance(driver['languages'], list)
        assert len(driver['languages']) == 1
        assert 'fr' in driver['languages']
