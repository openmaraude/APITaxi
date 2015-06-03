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
    'taxi_id': 1,
    'operateur': 'user_operateur'
}
class TestHailPost(Skeleton):
    url = '/hails/'
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

    def test_received_by_operator(self):
        u = User.query.filter_by(email='user_operateur').first()
        u.hail_endpoint = 'http://127.0.0.1:5001/hail/'
        taxi = self.post_taxi()
        formatted_value = Taxi._FORMAT_OPERATOR.format(timestamp=int(time.time()), lat=1,
            lon=1, status='free', device='d1', version=1)
        redis_store.hset('taxi:{}'.format(taxi['id']), 'user_operateur',
                formatted_value)
        dict_hail = deepcopy(dict_)
        dict_hail['taxi_id'] = taxi['id']
        r = None
        try:
            r = self.post([dict_hail])
        except ServiceUnavailable:
            pass
        self.assert201(r)
        self.assertEqual(len(Customer.query.all()), 1)
        self.assertEqual(len(Hail.query.all()), 1)
        self.assertEqual(r.json['data'][0]['status'], 'received_by_operator')

    def test_failure(self):
        u = User.query.filter_by(email='user_operateur').first()
        u.hail_endpoint = 'http://127.0.0.1:5001/hails_failure/'
        taxi = self.post_taxi()
        formatted_value = Taxi._FORMAT_OPERATOR.format(timestamp=int(time.time()), lat=1,
            lon=1, status='free', device='d1', version=1)
        redis_store.hset('taxi:{}'.format(taxi['id']), 'user_operateur',
                formatted_value)
        dict_hail = deepcopy(dict_)
        dict_hail['taxi_id'] = taxi['id']
        r = None
        try:
            r = self.post([dict_hail])
        except ServiceUnavailable:
            pass
        self.assert201(r)
        self.assertEqual(len(Customer.query.all()), 1)
        self.assertEqual(len(Hail.query.all()), 1)
        self.assertEqual(r.json['data'][0]['status'], 'failure')

    def post_taxi(self):
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
