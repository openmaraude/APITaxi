# -*- coding: utf-8 -*-
from APITaxi.extensions import redis_store_saved
from .skeleton import Skeleton
from .fake_data import dict_vehicle, dict_ads, dict_driver, dict_taxi, dict_hail as dict_
from APITaxi_models.hail import (Customer, Hail, rating_ride_reason_enum,
        incident_customer_reason_enum, incident_taxi_reason_enum,
        reporting_customer_reason_enum)
from APITaxi_models.taxis import Taxi
from APITaxi_models.security import User
from copy import deepcopy
from werkzeug.exceptions import ServiceUnavailable
from datetime import datetime, timedelta
import time, json
from flask import current_app

class HailMixin(Skeleton):
    url = '/hails/'

    def set_env(self, env, url, user='user_operateur'):
        from APITaxi_models.security import User
        prev_env = self.app.config['ENV']
        self.app.config['ENV'] = env
        u = User.query.filter_by(email=user).first()
        if env == 'PROD':
            u.hail_endpoint_production = url
        elif env == 'DEV':
            u.hail_endpoint_testing = url
        elif env == 'STAGING':
            u.hail_endpoint_staging = url
        current_app.extensions['sqlalchemy'].db.session.add(u)
        current_app.extensions['sqlalchemy'].db.session.commit()
        return prev_env

    def send_hail(self, dict_hail, method="post", role='moteur', apikey=False):
        user_operator = 'user_apikey' if apikey else 'user_operateur'
        taxi = self.post_taxi_and_locate(user=user_operator)
        dict_hail['taxi_id'] = taxi['id']
        r = None
        try:
            r = self.post([dict_hail], role=role, url='/hails/')
        except ServiceUnavailable:
            pass
        return r

    @classmethod
    def set_hail_status(cls, r, status, last_status_change=None):
        assert r.status_code == 200 or r.status_code == 201
        hail_id = r.json['data'][0]['id']
        hail = Hail.query.get(hail_id)
        hail._status = status
        setattr(hail, "change_to_" + status, datetime.now())
        if last_status_change:
            hail.last_status_change -= last_status_change
            for change_to in [v for v in dir(Hail) if v.startswith('change_to')]:
                val = getattr(hail, change_to)
                if not val:
                    continue
                setattr(hail, change_to,  val - last_status_change)
        current_app.extensions['sqlalchemy'].db.session.commit()

    def wait_for_status(self, status, hail_id):
        for i in range(1, 40):
            r = self.get('hails/{}/'.format(hail_id))
            if r.status_code == 200 and r.json['data'][0]['status'] == status:
                break
            time.sleep(i*0.001)
        return r

    def reset_customers(self):
        for c in Customer.query.all():
            c.reprieve_end = None
            c.ban_end = None
            c.reprieve_begin = None
            c.ban_begin = None
            current_app.extensions['sqlalchemy'].db.session.add(c)
        current_app.extensions['sqlalchemy'].db.session.commit()
class TestHailPost(HailMixin):
    role = 'moteur'

    def test_no_data(self):
        r = self.post({}, envelope_data=False)
        self.assert400(r)

    def test_too_many(self):
        r = self.post([dict_, dict_])
        self.assertEqual(r.status_code, 400)

    def test_missing_fields(self):
        dict_ = {
            'customer_id': 'aa',
            'taxi_id': 'a'
        }
        r = self.post([dict_])
        self.assert400(r)

    def test_no_taxi(self):
        before = set(redis_store_saved.keys("hail:notposted:*"))
        r = self.post([dict_])
        self.assert404(r)
        after = set(redis_store_saved.keys("hail:notposted:*"))
        keys = after - before
        assert len(keys) == 1
        key = keys.pop()
        scan = redis_store_saved.zscan_iter(key)
        val, score = scan.next()
        j = json.loads(val)
        assert j['code'] == 404


    def test_taxi_non_free(self):
        dict_hail = deepcopy(dict_)
        taxi = self.post_taxi_and_locate()
        dict_hail['taxi_id'] = taxi['id']
        taxi['status'] = 'off'
        r = self.put([taxi], url='/taxis/{}/'.format(taxi['id']),
            role='operateur')
        self.assert200(r)
        dict_hail['taxi_id'] = taxi['id']
        r = self.post([dict_hail])
        self.assert403(r)

    def received_by_operator(self, env):
        prev_env = self.set_env(env, 'http://127.0.0.1:5001/hail/')
        d = deepcopy(dict_)
        r = self.send_hail(d)
        self.assert201(r)
        self.assertEqual(len(Customer.query.all()), 1)
        self.assertEqual(len(Hail.query.all()), 1)
        self.assertEqual(r.json['data'][0]['status'], 'received')
        assert 'initial_taxi_lat' not in r.json['data'][0]
        assert 'initial_taxi_lon' not in r.json['data'][0]
        assert 'creation_datetime' in r.json['data'][0]
        del d['taxi_id']
        self.check_req_vs_dict(r.json['data'][0], d)
        assert 'creation_datetime' in r.json['data'][0]
        assert r.json['data'][0]['creation_datetime'] is not None
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.assertEqual(r.json['data'][0]['status'], 'received_by_operator')
        assert('taxi_phone_number' in r.json['data'][0])
        self.assertEqual(r.json['data'][0]['taxi_phone_number'], 'aaa')
        r = self.get('taxis/{}/'.format(r.json['data'][0]['taxi']['id']),
                role='operateur')
        self.assert200(r)
        self.assertEqual(r.json['data'][0]['status'], 'answering')
        self.app.config['ENV'] = prev_env
        hail = Hail.query.all()[0]
        assert hail.change_to_received_by_operator

    def test_received_by_operator_prod(self):
        self.received_by_operator('PROD')

    def test_received_by_operator_dev(self):
        self.received_by_operator('DEV')

    def test_received_by_operator_staging(self):
        self.received_by_operator('STAGING')

    def test_received_by_operator_apikey(self):
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail_apikey/',
                'user_apikey')
        dict__ = deepcopy(dict_)
        dict__['operateur'] = 'user_apikey'
        r = self.send_hail(deepcopy(dict__), apikey=True)
        self.assert201(r)
        self.assertEqual(len(Customer.query.all()), 1)
        self.assertEqual(len(Hail.query.all()), 1)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.assertEqual(r.json['data'][0]['status'], 'received_by_operator')
        r = self.get('taxis/{}/'.format(r.json['data'][0]['taxi']['id']),
                user='user_apikey', role='operateur')
        self.assert200(r)
        self.assertEqual(r.json['data'][0]['status'], 'answering')
        self.app.config['ENV'] = prev_env

    def failure_operator(self, env):
        prev_env = self.set_env(env, 'http://127.0.0.1:5001/hail_failure/')
        r = self.send_hail(deepcopy(dict_))
        self.assert201(r)
        self.assertEqual(len(Customer.query.all()), 1)
        self.assertEqual(len(Hail.query.all()), 1)
        r = self.wait_for_status('failure', r.json['data'][0]['id'])
        self.assertEqual(r.json['data'][0]['status'], 'failure')
        self.app.config['ENV'] = prev_env

    def test_failure_operator_prod(self):
        self.failure_operator('PROD')

    def test_failure_operator_dev(self):
        self.failure_operator('DEV')

    def test_failure_operator_staging(self):
        self.failure_operator('STAGING')

    def no_hail_field(self, k):
        prev_env = self.set_env('DEV', 'http://127.0.0.1:5001/hail/')
        hail = deepcopy(dict_)
        del hail[k]
        r = self.send_hail(hail)
        self.assert400(r)

    def test_no_phone_number(self):
        self.no_hail_field('customer_phone_number')

    def test_no_address(self):
        self.no_hail_field('customer_address')

    def test_no_lon(self):
        self.no_hail_field('customer_lon')

    def test_no_lat(self):
        self.no_hail_field('customer_lat')

    def test_server_empty_answer(self):
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail_empty/')
        r = self.send_hail(dict_)
        self.assert201(r)
        self.app.config['ENV'] = prev_env

    def test_server_empty_taxi(self):
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail_empty_taxi/')
        r = self.send_hail(dict_)
        self.assert201(r)
        self.app.config['ENV'] = prev_env

    def test_hail_operator_header_dash(self):
        u = User.query.filter_by(email='user_operateur').first()
        u.hail_endpoint_testing = 'http://127.0.0.1:5001/hail/'
        old_value = u.operator_header_name
        u.operator_header_name = u'X-API-KEY'

        self.test_received_by_operator_apikey()

        u.operator_header_name = old_value
        u.hail_endpoint_testing = ''

    def test_hail_operator_header_special_char(self):
        u = User.query.filter_by(email='user_operateur').first()
        u.hail_endpoint_testing = 'http://127.0.0.1:5001/hail/'
        old_value = u.operator_header_name
        u.operator_header_name = u'&é"\'(-è_çà)'
        r = self.send_hail(dict_)
        self.assert201(r)
        u.operator_header_name = old_value
        u.hail_endpoint_testing = ''

    def test_hail_operator_api_key_dash(self):
        u = User.query.filter_by(email='user_operateur').first()
        u.hail_endpoint_testing = 'http://127.0.0.1:5001/hail/'
        old_value = u.operator_api_key
        u.operator_api_key = u'-'
        self.test_received_by_operator_apikey()
        u.operator_api_key = old_value
        u.hail_endpoint_testing = ''

    def test_hail_operator_api_key_special_char(self):
        u = User.query.filter_by(email='user_operateur').first()
        old_value = u.operator_api_key
        u.hail_endpoint_testing = 'http://127.0.0.1:5001/hail/'
        u.operator_api_key = u'&é"\'(-è_çà)'
        self.test_received_by_operator_apikey()
        u.operator_api_key = old_value
        u.hail_endpoint_testing = ''

    def test_hail_post_after_reporting_customer(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'accepted_by_customer')
        dict_hail['reporting_customer'] = True
        dict_hail['reporting_customer_reason'] = 'payment'
        #dict_hail['reporting_customer_reason'] = 'payment'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='operateur')
        self.assert200(r)

        r = self.send_hail(deepcopy(dict_))
        self.assert403(r)
        self.app.config['ENV'] = prev_env

    def test_hail_post_after_2_timeouts(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'accepted_by_taxi', timedelta(seconds=31))
        r = self.get('/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert200(r)

        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'accepted_by_taxi', timedelta(seconds=31))
        r = self.get('/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert200(r)

        r = self.send_hail(dict_hail)
        self.assert403(r)
        self.app.config['ENV'] = prev_env


class  TestHailGet(HailMixin):
    role = 'moteur'

    def test_access_moteur(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.get('/hails/{}/'.format(r.json['data'][0]['id']), role='moteur')
        self.assert200(r)
        self.assertGreater(r.json['data'][0]['taxi']['crowfly_distance'], 1)
        assert 'creation_datetime' in r.json['data'][0]
        self.app.config['ENV'] = prev_env

    def test_access_operateur(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.get('/hails/{}/'.format(r.json['data'][0]['id']), role='operateur')
        self.assert200(r)
        assert 'creation_datetime' in r.json['data'][0]
        self.app.config['ENV'] = prev_env

    def test_no_access_moteur(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.get('/hails/{}/'.format(r.json['data'][0]['id']),
                role='moteur', user='user_moteur_2')
        self.assert403(r)
        self.app.config['ENV'] = prev_env

    def test_no_access_operateur(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.get('/hails/{}/'.format(r.json['data'][0]['id']),
                role='operateur', user='user_operateur_2')
        self.assert403(r)
        self.app.config['ENV'] = prev_env

    def test_bad_http_accept(self):
        r = self.get('/hails/1/', role='operateur',
        accept='application/json; charset=utf-8')
        self.assert400(r)

    def test_customer_timeout(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'accepted_by_taxi', timedelta(seconds=31))
        r = self.get('/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert200(r)
        assert(r.json['data'][0]['status'] == 'timeout_customer')
        self.app.config['ENV'] = prev_env

    def test_taxi_timeout(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'received_by_taxi', timedelta(seconds=31))
        r = self.get('/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='operateur')
        self.assert200(r)
        assert(r.json['data'][0]['status'] == 'timeout_taxi')
        self.app.config['ENV'] = prev_env

    def test_technical_timeout(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        for status in ['received_by_operator', 'sent_to_operator']:
            r = self.send_hail(dict_hail)
            self.assert201(r)
            r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
            self.set_hail_status(r, status, timedelta(seconds=11))
            r = self.get('/hails/{}/'.format(r.json['data'][0]['id']),
                    version=2, role='operateur')
            self.assert200(r)
            assert(r.json['data'][0]['status'] == 'failure')
            self.app.config['ENV'] = prev_env

    def test_accepted_by_customer_timeout(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'accepted_by_customer', timedelta(seconds=30*60+1))
        hail_id = r.json['data'][0]['id']
        r = self.get('/hails/{}/'.format(hail_id),
                version=2, role='operateur')
        self.assert200(r)
        assert(r.json['data'][0]['status'] == 'accepted_by_customer')
        hail = Hail.query.get(hail_id)
        assert hail._status == 'timeout_accepted_by_customer'
        assert r.json['data'][0]['taxi']['position']['lon'] == 0
        assert r.json['data'][0]['taxi']['position']['lat'] == 0
        assert r.json['data'][0]['taxi']['last_update'] == 0
        self.app.config['ENV'] = prev_env

    def test_customer_on_board(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'accepted_by_customer')
        hail_id = r.json['data'][0]['id']
        hail = Hail.query.get(hail_id)
        assert hail._status == 'accepted_by_customer'
        r = self.get('/hails/{}/'.format(hail_id),
                version=2, role='operateur')
        self.assert200(r)
        assert(r.json['data'][0]['status'] == 'accepted_by_customer')
        r = self.put([{'status': 'occupied'}],
                     '/taxis/{}/'.format(dict_hail['taxi_id']),
                     version=2, role="operateur")
        hail = Hail.query.get(hail_id)
        assert hail._status == 'customer_on_board'
        r = self.get('/hails/{}/'.format(hail_id),
                version=2, role='operateur')
        self.assert200(r)
        assert(r.json['data'][0]['status'] == 'accepted_by_customer')
        assert r.json['data'][0]['taxi']['position']['lon'] == 0
        assert r.json['data'][0]['taxi']['position']['lat'] == 0
        assert r.json['data'][0]['taxi']['last_update'] == 0
        r = self.get('/hails/{}/'.format(hail_id),
                version=3, role='operateur')
        self.assert200(r)
        assert(r.json['data'][0]['status'] == 'customer_on_board')
        assert r.json['data'][0]['taxi']['position']['lon'] == 0
        assert r.json['data'][0]['taxi']['position']['lat'] == 0
        assert r.json['data'][0]['taxi']['last_update'] == 0
        self.app.config['ENV'] = prev_env

    def test_finished(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'accepted_by_customer')
        hail_id = r.json['data'][0]['id']
        hail = Hail.query.get(hail_id)
        assert hail._status == 'accepted_by_customer'
        r = self.get('/hails/{}/'.format(hail_id),
                version=2, role='operateur')
        self.assert200(r)
        assert(r.json['data'][0]['status'] == 'accepted_by_customer')
        r = self.put([{'status': 'free'}],
                     '/taxis/{}/'.format(dict_hail['taxi_id']),
                     version=2, role="operateur")
        hail = Hail.query.get(hail_id)
        assert hail._status == 'finished'
        assert hail.change_to_finished != None
        r = self.get('/hails/{}/'.format(hail_id),
                version=2, role='operateur')
        self.assert200(r)
        assert(r.json['data'][0]['status'] == 'accepted_by_customer')
        assert r.json['data'][0]['taxi']['position']['lon'] == 0
        assert r.json['data'][0]['taxi']['position']['lat'] == 0
        assert r.json['data'][0]['taxi']['last_update'] == 0
        self.app.config['ENV'] = prev_env

    def test_unattended_status_on_non_final_statuses(self):
        for taxi_status in ['free', 'off', 'occupied', 'oncoming']:
            for hail_status in [ 'emitted', 'received', 'sent_to_operator',
                                'received_by_operator', 'received_by_taxi']:
                dict_hail = deepcopy(dict_)
                prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
                r = self.send_hail(dict_hail)
                self.assert201(r)
                r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
                self.set_hail_status(r, hail_status)
                hail_id = r.json['data'][0]['id']
                hail = Hail.query.get(hail_id)
                assert hail._status == hail_status
                r = self.get('/hails/{}/'.format(hail_id),
                        version=2, role='operateur')
                self.assert200(r)
                assert(r.json['data'][0]['status'] == hail_status)
                r = self.put([{'status': taxi_status}],
                             '/taxis/{}/'.format(dict_hail['taxi_id']),
                             version=2, role="operateur")
                hail = Hail.query.get(hail_id)
                assert hail._status == hail_status
                r = self.get('/hails/{}/'.format(hail_id),
                        version=2, role='operateur')
                self.assert200(r)
                assert(r.json['data'][0]['status'] == hail_status)

    def test_taxi_update_sync_hail_status(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        hail_id = r.json['data'][0]['id']
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'accepted_by_customer')

        r = self.put([{'status': 'occupied'}],
                       '/taxis/{}/'.format(dict_hail['taxi_id']),
                       version=2, role="operateur")
        self.assert200(r)
        assert r.json['data'][0]['status'] == 'occupied'
        r = self.get('/hails/{}/'.format(hail_id), version=3)
        assert r.json['data'][0]['status'] == 'customer_on_board'

        r = self.put([{'status': 'free'}],
                       '/taxis/{}/'.format(dict_hail['taxi_id']),
                       version=2, role="operateur")
        self.assert200(r)
        assert r.json['data'][0]['status'] == 'free'
        r = self.get('/hails/{}/'.format(hail_id), version=3)
        assert r.json['data'][0]['status'] == 'finished'
        self.app.config['ENV'] = prev_env

    def test_put_status_on_final_statuses(self):
        for taxi_status in ['free', 'off', 'occupied']:
            for hail_status in ['declined_by_taxi',  'incident_customer',
                                'incident_taxi', 'declined_by_customer',
                                'failure']:
                dict_hail = deepcopy(dict_)
                prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
                r = self.send_hail(dict_hail)
                self.assert201(r)
                r = self.wait_for_status('received_by_operator',
                                         r.json['data'][0]['id'])
                self.set_hail_status(r, hail_status)
                hail_id = r.json['data'][0]['id']
                hail = Hail.query.get(hail_id)
                assert hail._status == hail_status
                r = self.get('/hails/{}/'.format(hail_id),
                        version=2, role='operateur')
                self.assert200(r)
                assert(r.json['data'][0]['status'] == hail_status)
                r = self.put([{'status': taxi_status}],
                             '/taxis/{}/'.format(dict_hail['taxi_id']),
                             version=2, role="operateur")
                hail = Hail.query.get(hail_id)
                assert hail._status == hail_status
                r = self.get('/hails/{}/'.format(hail_id),
                        version=2, role='operateur')
                self.assert200(r)
                assert(r.json['data'][0]['status'] == hail_status)
                taxi = Taxi.query.get(dict_hail['taxi_id'])
                assert taxi.current_hail == None
        #test timeout taxi
        for taxi_status in ['free', 'off', 'occupied']:
            dict_hail = deepcopy(dict_)
            prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
            r = self.send_hail(dict_hail)
            self.assert201(r)
            r = self.wait_for_status('received_by_operator',
                                     r.json['data'][0]['id'])
            self.set_hail_status(r, 'received_by_taxi', timedelta(seconds=31))
            hail_id = r.json['data'][0]['id']
            r = self.get('/hails/{}/'.format(hail_id),
                    version=2, role='operateur')
            self.assert200(r)
            assert(r.json['data'][0]['status'] == 'timeout_taxi')
            r = self.put([{'status': taxi_status}],
                         '/taxis/{}/'.format(dict_hail['taxi_id']),
                         version=2, role="operateur")
            hail = Hail.query.get(hail_id)
            assert hail._status == 'timeout_taxi'
            r = self.get('/hails/{}/'.format(hail_id),
                    version=2, role='operateur')
            self.assert200(r)
            assert(r.json['data'][0]['status'] == 'timeout_taxi')
            taxi = Taxi.query.get(dict_hail['taxi_id'])
            assert taxi.current_hail == None
        #test timeout customer
        for taxi_status in ['free', 'off', 'occupied']:
            dict_hail = deepcopy(dict_)
            dict_hail['customer_id'] = '{}:{}'.format(dict_hail['customer_id'],
                                                      time.time())

            prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
            r = self.send_hail(dict_hail)
            self.assert201(r)
            r = self.wait_for_status('received_by_operator',
                                     r.json['data'][0]['id'])
            self.set_hail_status(r, 'accepted_by_taxi', timedelta(seconds=31))
            hail_id = r.json['data'][0]['id']
            r = self.get('/hails/{}/'.format(hail_id),
                    version=2, role='operateur')
            self.assert200(r)
            assert(r.json['data'][0]['status'] == 'timeout_customer')
            r = self.put([{'status': taxi_status}],
                         '/taxis/{}/'.format(dict_hail['taxi_id']),
                         version=2, role="operateur")
            hail = Hail.query.get(hail_id)
            assert hail._status == 'timeout_customer'
            r = self.get('/hails/{}/'.format(hail_id),
                    version=2, role='operateur')
            self.assert200(r)
            assert(r.json['data'][0]['status'] == 'timeout_customer')
            taxi = Taxi.query.get(dict_hail['taxi_id'])
            assert taxi.current_hail == None


class TestHailPut(HailMixin):
    role = 'operateur'

    def test_received_by_taxi_ok_version_1(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'received_by_taxi')
        dict_hail['taxi_phone_number'] = '000000'
        dict_hail['status'] = 'accepted_by_taxi'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']))
        self.assert200(r)
        self.app.config['ENV'] = prev_env

    def test_received_by_taxi_no_phone_number_version_1(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'received_by_taxi')
        dict_hail['status'] = 'accepted_by_taxi'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']))
        self.assert400(r)
        self.app.config['ENV'] = prev_env

    def test_received_by_taxi_ok_version_2(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'received_by_taxi')

        dict_hail['taxi_phone_number'] = '000000'
        dict_hail['status'] = 'accepted_by_taxi'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2)
        self.assert200(r)
        self.app.config['ENV'] = prev_env

    def test_received_by_taxi_no_phone_number_version_2(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'received_by_taxi')
        dict_hail['status'] = 'accepted_by_taxi'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2)
        self.assert400(r)
        self.app.config['ENV'] = prev_env

    def received_by_taxi_from_received(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'received')
        dict_hail['status'] = 'received_by_taxi'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2)
        self.assert200(r)
        assert r.json['data'][0]['status'] == 'received_by_taxi'
        assert 'creation_datetime' in r.json['data'][0]
        self.app.config['ENV'] = prev_env

    def received_by_operator_from_received_by_taxi(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'received_by_taxi')
        dict_hail['status'] = 'received_by_operator'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2)
        self.assert200(r)
        assert r.json['data'][0]['status'] == 'received_by_taxi'
        self.app.config['ENV'] = prev_env

    def test_timeout_taxi_ok(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'received_by_taxi', timedelta(seconds=10))
        dict_hail['taxi_phone_number'] = '000000'
        dict_hail['status'] = 'accepted_by_taxi'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2)
        self.assert200(r)
        assert(r.json['data'][0]['status'] == 'accepted_by_taxi')
        self.app.config['ENV'] = prev_env

    def test_timeout_taxi_ko(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'received_by_taxi', timedelta(seconds=31))
        dict_hail['taxi_phone_number'] = '000000'
        dict_hail['status'] = 'accepted_by_taxi'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2)
        self.assert200(r)
        assert(r.json['data'][0]['status'] == 'timeout_taxi')
        self.app.config['ENV'] = prev_env

    def test_timeout_customer_ok(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'accepted_by_taxi', timedelta(seconds=5))
        dict_hail['status'] = 'accepted_by_customer'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role="moteur")
        self.assert200(r)
        assert(r.json['data'][0]['status'] == 'accepted_by_customer')
        self.app.config['ENV'] = prev_env

    def test_timeout_customer_ko(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'accepted_by_taxi', timedelta(seconds=21))
        dict_hail['taxi_phone_number'] = '000000'
        dict_hail['status'] = 'accepted_by_customer'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role="moteur")
        self.assert200(r)
        assert(r.json['data'][0]['status'] == 'timeout_customer')
        self.app.config['ENV'] = prev_env

    def test_accepted_by_customer(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'accepted_by_taxi')
        dict_hail['status'] = 'accepted_by_customer'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role="moteur")
        self.assert200(r)
        assert(r.json['data'][0]['status'] == 'accepted_by_customer')
        self.app.config['ENV'] = prev_env

    def test_no_ban(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        for i in range(3):
            r = self.send_hail(dict_hail)
            self.assert201(r)
            r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
            self.set_hail_status(r, 'accepted_by_taxi')
            dict_hail['status'] = 'accepted_by_customer'
            r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                    version=2, role="moteur")
            self.assert200(r)
            assert(r.json['data'][0]['status'] == 'accepted_by_customer')
        self.app.config['ENV'] = prev_env

    def test_declined_by_customer(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'accepted_by_taxi')
        dict_hail['status'] = 'declined_by_customer'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role="moteur")
        self.assert200(r)
        assert(r.json['data'][0]['status'] == 'declined_by_customer')
        self.app.config['ENV'] = prev_env

    def test_invalid_status(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        dict_hail['status'] = 'string'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role="moteur")
        self.assert400(r)
        assert('Invalid status' in r.json['message'])
        self.app.config['ENV'] = prev_env

    def test_rating_ride_reason_all_valid_values(self):
        valid_values = ['ko', 'payment', 'courtesy', 'route', 'cleanliness']
        for v in valid_values:
            dict_hail = deepcopy(dict_)
            prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
            r = self.send_hail(dict_hail)
            self.assert201(r)
            r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
            hail = Hail.query.get(r.json['data'][0]['id'])
            hail._status = 'accepted_by_customer'
            dict_hail['status'] = 'accepted_by_customer'
            dict_hail['rating_ride_reason'] = v
            r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                    version=2, role='moteur')
            self.assert200(r)
            assert u'rating_ride_reason' in r.json['data'][0]
            assert r.json['data'][0]['rating_ride_reason'] == v
            self.app.config['ENV'] = prev_env

    def test_rating_ride_bad_value(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'accepted_by_customer'
        dict_hail['status'] = 'accepted_by_customer'
        dict_hail['rating_ride_reason'] = 'Une evaluation'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert400(r)
        self.app.config['ENV'] = prev_env

    def test_rating_ride_bad_value_with_accent(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'accepted_by_customer'
        dict_hail['status'] = 'accepted_by_customer'
        dict_hail['rating_ride_reason'] = 'Une évaluation'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert400(r)
        self.app.config['ENV'] = prev_env

    def test_rating_ride_by_non_moteur(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'accepted_by_customer'
        dict_hail['status'] = 'accepted_by_customer'
        dict_hail['rating_ride_reason'] = 'late'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2)
        self.assert403(r)

    def test_rating_ride(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'accepted_by_customer'
        dict_hail['status'] = 'accepted_by_customer'
        dict_hail['rating_ride'] = 2
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert200(r)
        assert  r.json['data'][0]['rating_ride'] == dict_hail['rating_ride']
        self.app.config['ENV'] = prev_env

    def test_rating_ride_2_hails(self):
        self.test_rating_ride()
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'accepted_by_customer'
        dict_hail['status'] = 'accepted_by_customer'
        dict_hail['rating_ride'] = 2
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert200(r)
        assert  r.json['data'][0]['rating_ride'] == dict_hail['rating_ride']
        assert  r.json['data'][0]['id'] == hail.id
        self.app.config['ENV'] = prev_env

    def test_rating_ride_one_null(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'accepted_by_customer'
        dict_hail['status'] = 'accepted_by_customer'
        dict_hail['rating_ride'] = None
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'accepted_by_customer'
        dict_hail['status'] = 'accepted_by_customer'
        dict_hail['rating_ride'] = 2
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.app.config['ENV'] = prev_env

    def test_rating_ride_no_status(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'accepted_by_customer'
        dict_hail['rating_ride'] = 2
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert200(r)
        assert  r.json['data'][0]['rating_ride'] == dict_hail['rating_ride']
        self.app.config['ENV'] = prev_env

    def test_rating_ride_min(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'accepted_by_customer'
        dict_hail['status'] = 'accepted_by_customer'
        dict_hail['rating_ride'] = 1
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert200(r)
        assert  r.json['data'][0]['rating_ride'] == dict_hail['rating_ride']
        self.app.config['ENV'] = prev_env

    def test_rating_ride_max(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'accepted_by_customer'
        dict_hail['status'] = 'accepted_by_customer'
        dict_hail['rating_ride'] = 5
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert200(r)
        assert  r.json['data'][0]['rating_ride'] == dict_hail['rating_ride']
        self.app.config['ENV'] = prev_env

    def test_rating_ride_bad_value(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'accepted_by_customer'
        dict_hail['status'] = 'accepted_by_customer'
        dict_hail['rating_ride'] = 6
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert400(r)
        self.app.config['ENV'] = prev_env

    def test_rating_ride_float(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'accepted_by_customer'
        dict_hail['status'] = 'accepted_by_customer'
        dict_hail['rating_ride'] = 1.
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert200(r)
        assert r.json['data'][0]['rating_ride'] == int(dict_hail['rating_ride'])
        taxi = Taxi.query.get(hail.taxi_id)
        assert taxi.rating < 4.5
        self.app.config['ENV'] = prev_env

    def test_rating_ride_string(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'accepted_by_customer'
        dict_hail['status'] = 'accepted_by_customer'
        dict_hail['rating_ride'] = 'pouet'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert400(r)
        self.app.config['ENV'] = prev_env

    def test_incident_customer_reason_all_valid_values(self):
        valid_values = ['', 'mud_river', 'parade', 'earthquake']
        for v in valid_values:
            dict_hail = deepcopy(dict_)
            prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
            r = self.send_hail(dict_hail)
            self.assert201(r)
            r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
            hail = Hail.query.get(r.json['data'][0]['id'])
            hail._status = 'incident_customer'
            dict_hail['status'] = 'incident_customer'
            dict_hail['incident_customer_reason'] = v
            r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                    version=2, role='moteur')
            self.assert200(r)
            assert u'incident_customer_reason' in r.json['data'][0]
            assert r.json['data'][0]['incident_customer_reason'] == v
            self.app.config['ENV'] = prev_env

    def test_ended_reprieve(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'accepted_by_customer'
        dict_hail['status'] = 'incident_customer'
        dict_hail['incident_customer_reason'] = 'mud_river'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert200(r)
        assert u'incident_customer_reason' in r.json['data'][0]
        assert r.json['data'][0]['incident_customer_reason'] == 'mud_river'
        customer = Customer.query.filter_by(id=hail.customer_id,
                                            moteur_id=hail.added_by).first()
        customer.reprieve_begin -= timedelta(days=1)
        customer.reprieve_end -= timedelta(days=1)
        current_app.extensions['sqlalchemy'].db.session.add(customer)
        current_app.extensions['sqlalchemy'].db.session.commit()

        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'accepted_by_customer'
        dict_hail['status'] = 'incident_customer'
        dict_hail['incident_customer_reason'] = 'mud_river'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert200(r)
        assert u'incident_customer_reason' in r.json['data'][0]
        assert r.json['data'][0]['incident_customer_reason'] == 'mud_river'

        customer = Customer.query.filter_by(id=hail.customer_id,
                                            moteur_id=hail.added_by).first()
        assert customer.ban_begin == None
        assert customer.ban_end == None
        assert customer.reprieve_end > datetime.now()


        self.app.config['ENV'] = prev_env

    def test_force_status_incident_customer(self):
        valid_values = ['', 'mud_river', 'parade', 'earthquake']
        for v in valid_values:
            dict_hail = deepcopy(dict_)
            prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
            r = self.send_hail(dict_hail)
            self.assert201(r)
            r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
            dict_hail['incident_customer_reason'] = v
            r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                    version=2, role='moteur')
            self.assert200(r)
            self.reset_customers()
            assert u'incident_customer_reason' in r.json['data'][0]
            assert r.json['data'][0]['incident_customer_reason'] == v
            assert r.json['data'][0]['status'] == 'incident_customer'
            self.app.config['ENV'] = prev_env

    def test_incident_customer_reason_bad_value(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'incident_customer'
        dict_hail['status'] = 'incident_customer'
        dict_hail['incident_customer_reason'] = 'Une evaluation'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert400(r)
        self.app.config['ENV'] = prev_env

    def test_incident_customer_reason_bad_value_with_accent(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'incident_customer'
        dict_hail['status'] = 'incident_customer'
        dict_hail['incident_customer_reason'] = 'Une évaluation'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='operateur')
        self.assert400(r)
        self.app.config['ENV'] = prev_env

    def test_incident_customer_by_non_moteur(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'incident_customer'
        dict_hail['status'] = 'incident_customer'
        dict_hail['incident_customer_reason'] = 'mud_river'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='operateur')
        self.assert403(r)

    def test_incident_taxi_reason_all_valid_values(self):
        valid_values = ['no_show', 'address', 'traffic', 'breakdown']
        for v in valid_values:
            dict_hail = deepcopy(dict_)
            prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
            r = self.send_hail(dict_hail)
            self.assert201(r)
            r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
            hail = Hail.query.get(r.json['data'][0]['id'])
            dict_hail['status'] = 'incident_taxi'
            dict_hail['incident_taxi_reason'] = v
            r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                    version=2, role='operateur')
            self.assert200(r)
            assert u'incident_taxi_reason' in r.json['data'][0]
            assert r.json['data'][0]['incident_taxi_reason'] == v
            r = self.get('/taxis/{}/'.format(hail.taxi_id))
            self.assert200(r)
            assert r.json['data'][0]['status'] == 'off'
            self.app.config['ENV'] = prev_env

    def test_force_status_incident_taxi(self):
        valid_values = ['no_show', 'address', 'traffic', 'breakdown']
        for v in valid_values:
            dict_hail = deepcopy(dict_)
            prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
            r = self.send_hail(dict_hail)
            self.assert201(r)
            r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
            dict_hail['incident_taxi_reason'] = v
            r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                    version=2, role='operateur')
            self.assert200(r)
            assert u'incident_taxi_reason' in r.json['data'][0]
            assert r.json['data'][0]['incident_taxi_reason'] == v
            assert r.json['data'][0]['status'] == 'incident_taxi'
            self.app.config['ENV'] = prev_env

    def test_incident_taxi_reason_bad_value(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'incident_taxi'
        dict_hail['status'] = 'incident_taxi'
        dict_hail['incident_taxi_reason'] = 'Une evaluation'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='operateur')
        self.assert400(r)
        self.app.config['ENV'] = prev_env

    def test_incident_taxi_reason_bad_value_with_accent(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'incident_taxi'
        dict_hail['status'] = 'incident_taxi'
        dict_hail['incident_taxi_reason'] = 'Une évaluation'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='operateur')
        self.assert400(r)
        self.app.config['ENV'] = prev_env

    def test_incident_taxi_by_non_operateur(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'incident_taxi'
        dict_hail['status'] = 'incident_taxi'
        dict_hail['incident_taxi_reason'] = 'traffic_jam'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert403(r)

    def test_reporting_customer(self):
        for v in [True, False]:
            dict_hail = deepcopy(dict_)
            prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
            r = self.send_hail(dict_hail)
            self.assert201(r)
            r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
            hail = Hail.query.get(r.json['data'][0]['id'])
            hail._status = 'accepted_by_customer'
            dict_hail['status'] = 'accepted_by_customer'
            dict_hail['reporting_customer'] = v
            r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                    version=2, role='operateur')
            self.assert200(r)
            assert u'reporting_customer' in r.json['data'][0]
            assert r.json['data'][0]['reporting_customer'] == v
            self.reset_customers()
            self.app.config['ENV'] = prev_env

    def test_reporting_customer_by_non_operateur(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'accepted_by_customer'
        dict_hail['status'] = 'accepted_by_customer'
        dict_hail['reporting_customer'] = True
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert403(r)

    def test_reporting_customer_reason_all_valid_values(self):
        valid_values = ['ko', 'payment', 'courtesy', 'route', 'cleanliness']
        for v in valid_values:
            dict_hail = deepcopy(dict_)
            prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
            r = self.send_hail(dict_hail)
            self.assert201(r)
            r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
            hail = Hail.query.get(r.json['data'][0]['id'])
            hail._status = 'accepted_by_customer'
            dict_hail['status'] = 'accepted_by_customer'
            dict_hail['reporting_customer_reason'] = v
            r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                    version=2, role='operateur')
            self.assert200(r)
            assert u'reporting_customer_reason' in r.json['data'][0]
            assert r.json['data'][0]['reporting_customer_reason'] == v
            self.app.config['ENV'] = prev_env

    def test_reporting_customer_reason_bad_value(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'accepted_by_customer'
        dict_hail['status'] = 'reporting_customer'
        dict_hail['reporting_customer_reason'] = 'Une evaluation'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='operateur')
        self.assert400(r)
        self.app.config['ENV'] = prev_env

    def test_reporting_customer_reason_bad_value_with_accent(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'accepted_by_customer'
        dict_hail['status'] = 'reporting_customer'
        dict_hail['reporting_customer_reason'] = 'Une évaluation'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='operateur')
        self.assert400(r)
        self.app.config['ENV'] = prev_env

    def test_reporting_customer_reason_by_non_operateur(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail._status = 'accepted_by_customer'
        dict_hail['status'] = 'accepted_by_customer'
        dict_hail['reporting_customer_reason'] = 'no_show'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert403(r)

    def test_empty_dict(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'received_by_taxi')
        r = self.put([{}], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2)
        self.assert200(r)
        self.app.config['ENV'] = prev_env

    def test_put_customer_operateur(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.set_hail_status(r, 'received_by_taxi')
        r = self.put([{'customer_lon':33}], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='operateur')
        self.assert200(r)
        assert r.json['data'][0]['customer_lon'] == dict_hail['customer_lon']
        self.app.config['ENV'] = prev_env

    def test_received_by_customer(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        dict_hail = {
            "taxi_phone_number": "+33624913387",
            "status": "received_by_taxi", 
        }
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2
        )
        self.assert200(r)
        self.app.config['ENV'] = prev_env
