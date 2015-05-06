from flask.ext.testing import TestCase
from requests import get
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
            db.session.commit()


    def tearDown(self):
        db.session.remove()
        db.drop_all()


    def check_req_vs_dict(self, req, dict_):
        map(lambda (k, v):
                self.assertIn(k, req) and self.assertEqual(v, dict_[k]),
                    dict_.iteritems())
    def call(self, data, url, envelope_data, role, fun):
        if not role:
            role = self.__class__.role
        authorization = "user_{}:{}".format(role, role)
        if envelope_data:
            data = {"data": data}
        if not url:
            url = self.__class__.url
        return fun(url, data=dumps(data),
                                headers={
                                    "Content-Type": "application/json",
                                    "Authorization": authorization
                                })

    def post(self, data, url=None, envelope_data=True, role=None):
        return self.call(data, url, envelope_data, role, self.client.post)

    def put(self, data, url=None, envelope_data=True, role=None):
        return self.call(data, url, envelope_data, role, self.client.put)

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
