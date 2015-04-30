from flask.ext.testing import TestCase
from requests import get
from json import dumps

from APITaxi import db, create_app, user_datastore
from APITaxi.api import api

class Skeleton(TestCase):

    TESTING = True

    def create_app(self):
        app = create_app(get('http://api.postgression.com').text)
        return app

    def setUp(self):
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
