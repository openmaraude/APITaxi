# -*- coding: utf-8 -*-

from flask.ext.testing import TestCase
from json import dumps

from APITaxi import db, create_app, user_datastore
from APITaxi.api import api
from APITaxi.models.administrative import Departement


class Skeleton(TestCase):
    TESTING = True

    def create_app(self):
        return create_app()

    def setUp(self):
        db.drop_all()
        db.create_all()
        for role in ['admin', 'operateur', 'moteur']:
            r = user_datastore.create_role(name=role)
            u = user_datastore.create_user(email='user_'+role,
                                           password=role)
            user_datastore.add_role_to_user(u, r)
            u = user_datastore.create_user(email='user_'+role+'_2',
                                           password=role)
            user_datastore.add_role_to_user(u, r)
            db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def check_req_vs_dict(self, req, dict_):
        for k, v in dict_.items():
            self.assertIn(k, req)
            if type(req[k]) is dict:
                self.check_req_vs_dict(req[k], dict_[k])
            else:
                self.assertEqual(v, req[k])

    def call(self, url, role, user, fun, data=None, envelope_data=None):
        if not role:
            role = self.__class__.role
        if not user:
            user = 'user_{}'.format(role)
        authorization = "{}:{}".format(user, role)
        if envelope_data:
            data = {"data": data}
        data = dumps(data) if data else data
        if not url:
            url = self.__class__.url
        return fun(url, data=data,
                                headers={
                                    "Authorization": authorization,
                                    "Accept": "application/json",
                                    "X-VERSION": 1
                                },
                   content_type='application/json')

    def get(self, url, role=None, user=None):
        return self.call(url, role, user, self.client.get)

    def post(self, data, url=None, envelope_data=True, role=None, user=None):
        return self.call(url, role, user, self.client.post, data, envelope_data)

    def put(self, data, url=None, envelope_data=True, role=None, user=None):
        return self.call(url, role, user, self.client.put, data, envelope_data)

    def init_dep(self):
        dep = Departement()
        dep.nom = "Mayenne"
        dep.numero = "53"
        db.session.add(dep)
        db.session.commit()

    def assert201(self, request):
        self.assertEqual(request.status_code, 201)

    def assert503(self, request):
        self.assertEqual(request.status_code, 503)
