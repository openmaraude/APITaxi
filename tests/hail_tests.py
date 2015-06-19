from .skeleton import Skeleton
from .fake_data import dict_vehicle, dict_ads, dict_driver, dict_taxi
from APITaxi.models.hail import Customer, Hail
from APITaxi.models.taxis import Taxi
from APITaxi.models.security import User
from APITaxi import redis_store
from copy import deepcopy
from functools import partial
from werkzeug.exceptions import ServiceUnavailable
import time

dict_ = {
    'customer_id': 'aa',
    'customer_lon': 4.4,
    'customer_lat': 0,
    'customer_address': 'Pas loin, Paris',
    'customer_phone_number': '067372727',
    'taxi_id': 1,
    'operateur': 'user_operateur'
}
class HailMixin(Skeleton):
    url = '/hails/'

    def set_env(self, env, url):
        prev_env = self.app.config['ENV']
        self.app.config['ENV'] = env
        u = User.query.filter_by(email='user_operateur').first()
        if env == 'PROD':
            u.hail_endpoint_production = url
        elif env == 'DEV':
            u.hail_endpoint_testing = url
        elif env == 'STAGING':
            u.hail_endpoint_staging = url
        return prev_env

    def send_hail(self, dict_hail, method="post", role=None):
        taxi = self.post_taxi()
        formatted_value = Taxi._FORMAT_OPERATOR.format(timestamp=int(time.time()), lat=1,
            lon=1, status='free', device='d1', version=1)
        redis_store.hset('taxi:{}'.format(taxi['id']), 'user_operateur',
                formatted_value)
        dict_hail['taxi_id'] = taxi['id']
        r = None
        try:
            r = self.post([dict_hail], role='moteur')
        except ServiceUnavailable:
            pass
        return r

    def post_taxi(self, role=None):
        post = partial(self.post, role='operateur')
        self.init_dep()
        post([dict_driver], url='/drivers/')
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

class TestHailPost(HailMixin):
    role = 'moteur'

    def test_no_data(self):
        r = self.post({}, envelope_data=False)
        self.assert400(r)

    def test_too_many(self):
        r = self.post([{}, {}])
        self.assertEqual(r.status_code, 413)

    def test_missing_fields(self):
        dict_ = {
            'customer_id': 'aa',
            'taxi_id': 1
        }
        r = self.post([dict_])
        self.assert400(r)

    def test_no_taxi(self):
        r = self.post([dict_])
        self.assert404(r)

    def test_taxi_non_free(self):
        dict_hail = deepcopy(dict_)
        taxi = self.post_taxi()
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
        self.assertEqual(r.json['data'][0]['status'], 'received_by_operator')
        self.app.config['ENV'] = prev_env

    def test_received_by_operator_prod(self):
        self.received_by_operator('PROD')

    def test_received_by_operator_dev(self):
        self.received_by_operator('DEV')

    def test_received_by_operator_staging(self):
        self.received_by_operator('STAGING')


    def failure_operator(self, env):
        prev_env = self.set_env(env, 'http://127.0.0.1:5001/hail_failure/')
        r = self.send_hail(deepcopy(dict_))
        self.assert201(r)
        self.assertEqual(len(Customer.query.all()), 1)
        self.assertEqual(len(Hail.query.all()), 1)
        self.assertEqual(r.json['data'][0]['status'], 'failure')
        self.app.config['ENV'] = prev_env

    def test_failure_operator_prod(self):
        self.failure_operator('PROD')

    def test_failure_operator_dev(self):
        self.failure_operator('DEV')

    def test_failure_operator_staging(self):
        self.failure_operator('STAGING')

    def test_no_address(self):
        prev_env = self.set_env('DEV', 'http://127.0.0.1:5001/hail/')
        hail = deepcopy(dict_)
        del hail['customer_address']
        r = self.send_hail(hail)
        self.assert400(r)

    def test_no_phone_number(self):
        prev_env = self.set_env('DEV', 'http://127.0.0.1:5001/hail/')
        hail = deepcopy(dict_)
        del hail['customer_phone_number']
        r = self.send_hail(hail)
        self.assert400(r)

class TestHailPut(HailMixin):
    role = 'operateur'

    def test_received_by_taxi_ok(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        dict_hail['taxi_phone_number'] = '000000'
        dict_hail['status'] = 'received_by_taxi'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']))
        print r.json
        self.assert200(r)
        self.app.config['ENV'] = prev_env

    def test_received_by_taxi_no_phone_number(self):
        dict_hail = deepcopy(dict_)
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        r = self.send_hail(dict_hail)
        self.assert201(r)
        dict_hail['status'] = 'received_by_taxi'
        r = self.put([dict_hail], '/hails/{}/'.format(r.json['data'][0]['id']))
        self.assert400(r)
        self.app.config['ENV'] = prev_env

