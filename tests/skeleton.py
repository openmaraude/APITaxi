# -*- coding: utf-8 -*-

from flask_testing import TestCase
from json import dumps
from APITaxi import create_app
from APITaxi.extensions import (redis_store, user_datastore)
from APITaxi.api import api
import APITaxi_models as models
from APITaxi_models import db
from functools import partial
from .fake_data import (dict_driver, dict_vehicle, dict_ads, dict_taxi,
    dict_driver_2, dict_vehicle_2, dict_ads_2, dict_taxi_2)
from copy import deepcopy
import time
from shapely.geometry import Polygon, MultiPolygon
from geoalchemy2.shape import from_shape
from flask_login import current_user
from flask import current_app

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
        r = user_datastore.find_role('operateur')
        u = user_datastore.create_user(email='user_apikey',
                password='operateur')
        u.operator_header_name = 'X-API-KEY'
        u.operator_api_key = 'xxx'
        user_datastore.add_role_to_user(u, r)
        db.session.commit()

    def tearDown(self):
        ids = []
        for taxi in models.Taxi.query.all():
            redis_store.delete('taxi:{}'.format(taxi.id))
        for k, v in list(current_app.config.items()):
            if not k.startswith('REDIS'):
                continue
            redis_store.delete(v)
        current_app.extensions['sqlalchemy'].db.session.remove()
        current_app.extensions['sqlalchemy'].db.drop_all()
        current_app.extensions['sqlalchemy'].db.get_engine(self.app).dispose()


    def post_taxi(self, role=None, user=None, post_second=False, custom_ads=None):
        self.init_zupc(post_second)
        post = partial(self.post, role='operateur', user=user)
        self.init_dep()
        if post_second:
            r = post([dict_driver_2], url='/drivers/')
        else:
            r = post([dict_driver], url='/drivers/')
        self.assert201(r)
        if post_second:
            r = post([dict_vehicle_2], url='/vehicles/')
        else:
            r = post([dict_vehicle], url='/vehicles/')
        self.assert201(r)
        vehicle_id = r.json['data'][0]['id']
        if custom_ads:
            dict_ads_ = deepcopy(custom_ads)
        elif post_second:
            dict_ads_ = deepcopy(dict_ads_2)
        else:
            dict_ads_ = deepcopy(dict_ads)
        dict_ads_['vehicle_id'] = vehicle_id
        post([dict_ads_], url='/ads/')
        if custom_ads:
            dict_taxi_ = deepcopy(dict_taxi)
            dict_taxi_["ads"]["insee"] = dict_ads_["insee"]
            dict_taxi_["ads"]["numero"] = dict_ads_["numero"]
            r = post([dict_taxi_], url='/taxis/')
        elif post_second:
            r = post([dict_taxi_2], url='/taxis/')
        else:
            r = post([dict_taxi], url='/taxis/')
        self.assert201(r)
        taxi = r.json['data'][0]
        return taxi

    def post_taxi_and_locate(self, lat=1, lon=1, user='user_operateur',
            float_=False, post_second=False, custom_ads=None):
        taxi = self.post_taxi(user=user, post_second=post_second, custom_ads=custom_ads)
        timestamp_type = float if float_ else int
        values = [timestamp_type(time.time()), lat, lon, 'free', 'd1', 1]
        redis_store.hset('taxi:{}'.format(taxi['id']), user,
                ' '.join([str(v) for v in values]))
        n = '{}:{}'.format(taxi['id'], user)
        redis_store.geoadd(current_app.config['REDIS_GEOINDEX'], lat, lon, n)
        redis_store.zadd(current_app.config['REDIS_TIMESTAMPS'], {n:time.time()})
        redis_store.geoadd(current_app.config['REDIS_GEOINDEX_ID'], lat, lon, taxi['id'])
        redis_store.zadd(current_app.config['REDIS_TIMESTAMPS_ID'], {taxi['id']:time.time()})
        return taxi

    def init_zupc(self, post_second=False):
        zupc = models.ZUPC()
        zupc.insee = '75056' if not post_second else '34172'
        zupc.nom = 'Paris' if not post_second else 'Montpellier'
        if post_second:
            poly = Polygon([(43.7, 3.7), (43.7, 4.4), (43.4, 4.4), (43.4, 3.7)])
        else:
            poly = Polygon([(48,2), (49,2), (49,3), (48,3)])
        zupc.shape = from_shape(MultiPolygon([poly]), srid=4326)
        db.session.add(zupc)
        db.session.commit()
        zupc.parent_id = zupc.id

        zupc2 = models.ZUPC()
        zupc2.insee = '93048'
        zupc2.nom = 'Montreuil'
        zupc2.parent_id = zupc.id
        db.session.add(zupc2)
        db.session.commit()

    def check_req_vs_dict(self, req, dict_):
        for k, v in list(dict_.items()):
            self.assertIn(k, req)
            if type(req[k]) is dict:
                self.check_req_vs_dict(req[k], dict_[k])
            else:
                self.assertEqual(v, req[k])

    def call(self, url, role, user, fun, data=None, envelope_data=None,
            version=2, accept="application/json",
            content_type='application/json', headers={}):
        if not role and not headers:
            role = self.__class__.role
        if not user and not headers:
            user = 'user_{}'.format(role)
        authorization = "{}:{}".format(user, role)
        if envelope_data:
            data = {"data": data}
        data = dumps(data) if data and content_type else data
        if not url:
            url = self.__class__.url
        if not headers:
            headers={"Authorization": authorization,
                     "Accept": accept,
                     "X-VERSION": version
            }

        with self.app.test_client() as c:
            return getattr(c, fun)(url, data=data,
                        headers=headers,
                        content_type=content_type)

    def get(self, url=None, role=None, user=None, version=2,
            accept="application/json", headers={}):
        return self.call(url, role, user, "get", version=version,
                accept=accept, headers=headers)

    def post(self, data, url=None, envelope_data=True, role=None, user=None,
            version=2, content_type='application/json',
            accept='application/json', headers={}):
        return self.call(url, role, user, "post", data, envelope_data,
            version=version, content_type=content_type, accept=accept,
                         headers=headers)

    def put(self, data, url=None, envelope_data=True, role=None, user=None,
            version=2, content_type='application/json', headers={}):
        return self.call(url, role, user, "put", data, envelope_data,
            version=version, content_type=content_type, headers=headers)

    def init_dep(self):
        dep = models.Departement()
        dep.nom = "Mayenne"
        dep.numero = "53"
        current_app.extensions['sqlalchemy'].db.session.add(dep)
        current_app.extensions['sqlalchemy'].db.session.commit()

    def assert201(self, request):
        try:
            self.assertEqual(request.status_code, 201)
        except AssertionError as e:
            print(request.json)
            raise e

    def assert503(self, request):
        self.assertEqual(request.status_code, 503)
