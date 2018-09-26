# -*- coding: utf-8 -*-
from .skeleton import Skeleton

class TestUsersGet(Skeleton):
    url = '/users/'
    def test_get_admin_user(self):
        r = self.get(role='admin')
        self.assert200(r)
        data = r.json['data']
        assert len(data) == 7
        assert all(['apikey' in d and 'name' in d for d in data])

    def test_get_operateur_user(self):
        r = self.get(role='operateur')
        assert r.status_code == 302

    def test_get_moteur_user(self):
        r = self.get(role='moteur')
        assert r.status_code == 302

    def test_get_no_login(self):
        r = self.get(headers={"X-API-KEY": "aa",
                              "Accept": "application/json",
                              "X-VERSION": 2})
        assert r.status_code == 302
