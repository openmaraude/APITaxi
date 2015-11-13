# -*- coding: utf-8 -*-
from APITaxi.extensions import db, redis_store, regions
from .skeleton import Skeleton
from .fake_data import dict_vehicle, dict_ads, dict_driver, dict_taxi
from APITaxi.models.hail import (Customer, Hail, rating_ride_reason_enum,
        incident_customer_reason_enum, incident_taxi_reason_enum,
        reporting_customer_reason_enum)
from APITaxi.models.taxis import Taxi
from copy import deepcopy
from werkzeug.exceptions import ServiceUnavailable
from datetime import datetime, timedelta
import time

dict_ = {
    'customer_id': 'aa',
    'customer_lon': 4.4,
    'customer_lat': 0,
    'customer_address': 'Pas loin, Paris',
    'customer_phone_number': '067372727',
    'taxi_id': 'aa',
    'operateur': 'user_operateur'
}
class HailMixin(Skeleton):
    url = '/hails/'

    def set_env(self, env, url, user='user_operateur'):
        from APITaxi.models.security import User
        prev_env = self.app.config['ENV']
        self.app.config['ENV'] = env
        u = User.query.filter_by(email=user).first()
        if env == 'PROD':
            u.hail_endpoint_production = url
        elif env == 'DEV':
            u.hail_endpoint_testing = url
        elif env == 'STAGING':
            u.hail_endpoint_staging = url
        db.session.add(u)
        db.session.commit()
        return prev_env

    def send_hail(self, dict_hail, method="post", role='moteur', apikey=False):
        user_operator = 'user_apikey' if apikey else 'user_operateur'
        taxi = self.post_taxi_and_locate(user=user_operator)
        dict_hail['taxi_id'] = taxi['id']
        r = None
        try:
            r = self.post([dict_hail], role=role)
        except ServiceUnavailable:
            pass
        return r

    @classmethod
    def set_hail_status(cls, r, status, last_status_change=None):
        regions['hails'].invalidate()
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail.__status_set_no_check(status)
        if last_status_change:
            hail.last_status_change -= last_status_change
        db.session.commit()

    def wait_for_status(self, status, hail_id):
        for i in range(1, 6):
            r = self.get('hails/{}/'.format(hail_id))
            if r.status_code == 200 and r.json['data'][0]['status'] == status:
                break
            time.sleep(i*0.001)
        return r

class TestHailPost(HailMixin):
    role = 'moteur'

    def test_no_data(self):
        r = self.post({}, envelope_data=False)
        self.assert400(r)

    def test_too_many(self):
        r = self.post([dict_, dict_])
        self.assertEqual(r.status_code, 413)

    def test_missing_fields(self):
        dict_ = {
            'customer_id': 'aa',
            'taxi_id': 'a'
        }
        r = self.post([dict_])
        self.assert400(r)

    def test_no_taxi(self):
        r = self.post([dict_])
        self.assert404(r)

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
        r = self.send_hail(deepcopy(dict_))
        self.assert201(r)
        self.assertEqual(len(Customer.query.all()), 1)
        self.assertEqual(len(Hail.query.all()), 1)
        self.assertEqual(r.json['data'][0]['status'], 'received')
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        self.assertEqual(r.json['data'][0]['status'], 'received_by_operator')
        assert('taxi_phone_number' in r.json['data'][0])
        self.assertEqual(r.json['data'][0]['taxi_phone_number'], 'aaa')
        r = self.get('taxis/{}/'.format(r.json['data'][0]['taxi']['id']),
                role='operateur')
        self.assert200(r)
        self.assertEqual(r.json['data'][0]['status'], 'answering')
        self.app.config['ENV'] = prev_env

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
        r = self.wait_for_status('received', r.json['data'][0]['id'])
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

    def test_no_address(self):
        self.no_hail_field('customer_address')

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
        self.app.config['ENV'] = prev_env

    def test_access_operateur(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.get('/hails/{}/'.format(r.json['data'][0]['id']), role='operateur')
        self.assert200(r)
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
        valid_values = ['late', 'no_credit_card', 'bad_itinerary', 'dirty_taxi']
        assert sorted(valid_values) == sorted(rating_ride_reason_enum)
        for v in valid_values:
            dict_hail = deepcopy(dict_)
            prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
            r = self.send_hail(dict_hail)
            self.assert201(r)
            r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
            hail = Hail.query.get(r.json['data'][0]['id'])
            hail.__status_set_no_check('accepted_by_customer')
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
        hail.__status_set_no_check('accepted_by_customer')
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
        hail.__status_set_no_check('accepted_by_customer')
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
        hail.__status_set_no_check('accepted_by_customer')
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
        hail.__status_set_no_check('accepted_by_customer')
        dict_hail['status'] = 'accepted_by_customer'
        dict_hail['rating_ride'] = 2
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert200(r)
        assert  r.json['data'][0]['rating_ride'] == dict_hail['rating_ride']
        self.app.config['ENV'] = prev_env

    def test_rating_ride_no_status(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail.__status_set_no_check('accepted_by_customer')
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
        hail.__status_set_no_check('accepted_by_customer')
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
        hail.__status_set_no_check('accepted_by_customer')
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
        hail.__status_set_no_check('accepted_by_customer')
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
        hail.__status_set_no_check('accepted_by_customer')
        dict_hail['status'] = 'accepted_by_customer'
        dict_hail['rating_ride'] = 2
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert200(r)
        assert r.json['data'][0]['rating_ride'] == int(dict_hail['rating_ride'])
        self.app.config['ENV'] = prev_env

    def test_rating_ride_string(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail.__status_set_no_check('accepted_by_customer')
        dict_hail['status'] = 'accepted_by_customer'
        dict_hail['rating_ride'] = 'pouet'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert400(r)
        self.app.config['ENV'] = prev_env

    def test_incident_customer_reason_all_valid_values(self):
        valid_values = ['mud_river', 'parade', 'earthquake']
        assert sorted(valid_values) == sorted(incident_customer_reason_enum)
        for v in valid_values:
            dict_hail = deepcopy(dict_)
            prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
            r = self.send_hail(dict_hail)
            self.assert201(r)
            r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
            hail = Hail.query.get(r.json['data'][0]['id'])
            hail.__status_set_no_check('incident_customer')
            dict_hail['status'] = 'incident_customer'
            dict_hail['incident_customer_reason'] = v
            r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                    version=2, role='moteur')
            self.assert200(r)
            assert u'incident_customer_reason' in r.json['data'][0]
            assert r.json['data'][0]['incident_customer_reason'] == v
            self.app.config['ENV'] = prev_env

    def test_incident_customer_reason_bad_value(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail.__status_set_no_check('incident_customer')
        dict_hail['status'] = 'incident_customer'
        dict_hail['incident_customer_reason'] = 'Une evaluation'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='operateur')
        self.assert400(r)
        self.app.config['ENV'] = prev_env

    def test_incident_customer_reason_bad_value_with_accent(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail.__status_set_no_check('incident_customer')
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
        hail.__status_set_no_check('incident_customer')
        dict_hail['status'] = 'incident_customer'
        dict_hail['incident_customer_reason'] = 'mud_river'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='operateur')
        self.assert403(r)

    def test_incident_taxi_reason_all_valid_values(self):
        valid_values = ['traffic_jam', 'garbage_truck']
        assert sorted(valid_values) == sorted(incident_taxi_reason_enum)
        for v in valid_values:
            dict_hail = deepcopy(dict_)
            prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
            r = self.send_hail(dict_hail)
            self.assert201(r)
            r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
            hail = Hail.query.get(r.json['data'][0]['id'])
            hail.__status_set_no_check('incident_taxi')
            dict_hail['status'] = 'incident_taxi'
            dict_hail['incident_taxi_reason'] = v
            r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                    version=2, role='operateur')
            self.assert200(r)
            assert u'incident_taxi_reason' in r.json['data'][0]
            assert r.json['data'][0]['incident_taxi_reason'] == v
            self.app.config['ENV'] = prev_env

    def test_incident_taxi_reason_bad_value(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail.__status_set_no_check('incident_taxi')
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
        hail.__status_set_no_check('incident_taxi')
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
        hail.__status_set_no_check('incident_taxi')
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
            hail.__status_set_no_check('accepted_by_customer')
            dict_hail['status'] = 'accepted_by_customer'
            dict_hail['reporting_customer'] = v
            r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                    version=2, role='operateur')
            self.assert200(r)
            assert u'reporting_customer' in r.json['data'][0]
            assert r.json['data'][0]['reporting_customer'] == v
            self.app.config['ENV'] = prev_env

    def test_reporting_customer_by_non_operateur(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
        hail = Hail.query.get(r.json['data'][0]['id'])
        hail.__status_set_no_check('accepted_by_customer')
        dict_hail['status'] = 'accepted_by_customer'
        dict_hail['reporting_customer'] = True
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert403(r)

    def test_reporting_customer_reason_all_valid_values(self):
        valid_values = ['late', 'aggressive', 'no_show']
        assert sorted(valid_values) == sorted(reporting_customer_reason_enum)
        for v in valid_values:
            dict_hail = deepcopy(dict_)
            prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
            r = self.send_hail(dict_hail)
            self.assert201(r)
            r = self.wait_for_status('received_by_operator', r.json['data'][0]['id'])
            hail = Hail.query.get(r.json['data'][0]['id'])
            hail.__status_set_no_check('accepted_by_customer')
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
        hail.__status_set_no_check('reporting_customer')
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
        hail.__status_set_no_check('reporting_customer')
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
        hail.__status_set_no_check('accepted_by_customer')
        dict_hail['status'] = 'accepted_by_customer'
        dict_hail['reporting_customer_reason'] = 'no_show'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='moteur')
        self.assert403(r)
