# -*- coding: utf-8 -*-

from flask.ext.testing import TestCase
from json import dumps
from APITaxi import create_app
from APITaxi.extensions import (db, redis_store, index_zupc, region_taxi,
                               region_hails, region_users, user_datastore)
from APITaxi.utils.login_manager import user_datastore
from APITaxi.api import api
from APITaxi.models.administrative import Departement, ZUPC
from APITaxi.models.taxis import Taxi
from functools import partial
from .fake_data import dict_driver, dict_vehicle, dict_ads, dict_taxi
from copy import deepcopy
import time
from shapely.geometry import Polygon, MultiPolygon
from geoalchemy2.shape import from_shape
from flask.ext.login import current_user

class Skeleton(TestCase):
    TESTING = True

    def create_app(self):
        return create_app()

    def setUp(self):
        db.drop_all()
        db.create_all()
        region_taxi.invalidate()
        region_hails.invalidate()
        region_users.invalidate()
        for role in ['admin', 'operateur', 'moteur']:
            r = user_datastore.create_role(name=role)
            u = user_datastore.create_user(email='user_'+role,
                                           password=role)
            user_datastore.add_role_to_user(u, r)
            u = user_datastore.create_user(email='user_'+role+'_2',
                                           password=role)
            user_datastore.add_role_to_user(u, r)
        db.session.commit()
        r = user_datastore.find_role('operateur')
        u = user_datastore.create_user(email='user_apikey',
                password='operateur')
        u.operator_header_name = 'X-API-KEY'
        u.operator_api_key = 'xxx'
        user_datastore.add_role_to_user(u, r)
        db.session.commit()

    def tearDown(self):
        ids = []
        for taxi in Taxi.query.all():
            redis_store.delete('taxi:{}'.format(taxi.id))
            ids.append(taxi.id)
        for i in ids:
            redis_store.zrem('geoindex', i)
        db.session.remove()
        db.drop_all()
        db.get_engine(self.app).dispose()
        region_taxi.invalidate()
        region_hails.invalidate()
        region_users.invalidate()
        index_zupc.index_zupc = None


    def post_taxi(self, role=None, user=None):
        self.init_zupc()
        post = partial(self.post, role='operateur', user=user)
        self.init_dep()
        r = post([dict_driver], url='/drivers/')
        self.assert201(r)
        r = post([dict_vehicle], url='/vehicles/')
        self.assert201(r)
        vehicle_id = r.json['data'][0]['id']
        dict_ads_ = deepcopy(dict_ads)
        dict_ads_['vehicle_id'] = vehicle_id
        post([dict_ads_], url='/ads/')
        r = post([dict_taxi], url='/taxis/')
        self.assert201(r)
        taxi = r.json['data'][0]
        return taxi

    def post_taxi_and_locate(self, lat=1, lon=1, user=None):
        taxi = self.post_taxi(user=user)
        formatted_value = Taxi._FORMAT_OPERATOR.format(timestamp=int(time.time()),
                lat=lat, lon=lon, status='free', device='d1', version=1)
        redis_store.hset('taxi:{}'.format(taxi['id']), user, formatted_value)
        redis_store.geoadd('geoindex', lat, lon, taxi['id'])
        return taxi

    def init_zupc(self):
        zupc = ZUPC()
        zupc.insee = '75056'
        zupc.nom = 'Paris'
        poly = Polygon([(48,2), (49,2), (49,3), (48,3)])
        zupc.shape = from_shape(MultiPolygon([poly]), srid=4326)
        db.session.add(zupc)
        db.session.commit()
        zupc.parent_id = zupc.id

        zupc2 = ZUPC()
        zupc2.insee = '93048'
        zupc2.nom = 'Montreuil'
        zupc2.parent_id = zupc.id
        db.session.add(zupc2)
        db.session.commit()

    def check_req_vs_dict(self, req, dict_):
        for k, v in dict_.items():
            self.assertIn(k, req)
            if type(req[k]) is dict:
                self.check_req_vs_dict(req[k], dict_[k])
            else:
                self.assertEqual(v, req[k])

    def call(self, url, role, user, fun, data=None, envelope_data=None,
            version=1, accept="application/json"):
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
        with self.app.test_client() as c:
            return getattr(c, fun)(url, data=data,
                        headers={
                            "Authorization": authorization,
                            "Accept": accept,
                            "X-VERSION": version},
                        content_type='application/json')

    def get(self, url, role=None, user=None, version=1,
            accept="application/json"):
        return self.call(url, role, user, "get", version=version,
                accept=accept)

    def post(self, data, url=None, envelope_data=True, role=None, user=None,
            version=1):
        return self.call(url, role, user, "post", data, envelope_data,
            version=version)

    def put(self, data, url=None, envelope_data=True, role=None, user=None,
            version=1):
        return self.call(url, role, user, "put", data, envelope_data,
            version=version)

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
