# -*- coding: utf-8 -*-
from .hail_tests import HailMixin
from copy import deepcopy
from APITaxi_models.hail import Customer as CustomerModel
from APITaxi.extensions import user_datastore

dict_hail = {
    'customer_id': 'aa',
    'customer_lon': 4.4,
    'customer_lat': 0,
    'customer_address': 'Pas loin, Paris',
    'customer_phone_number': '067372727',
    'taxi_id': 'aa',
    'operateur': 'user_operateur'
}
class TestCustomerPut(HailMixin):
    role = 'moteur'
    url = '/customers/'
    def test_put_empty(self):
        prev_env = self.set_env('PROD', 'http://127.0.0.1:5001/hail/')
        dict_ = deepcopy(dict_hail)
        r = self.send_hail(dict_hail)
        self.set_hail_status(r, 'accepted_by_customer')
        dict_['reporting_customer'] = True
        dict_['reporting_customer_reason'] = 'payment'
        r = self.put([dict_], '/hails/{}/'.format(r.json['data'][0]['id']),
                version=2, role='operateur')

        user_moteur = user_datastore.find_user(email='user_moteur')
        customer = CustomerModel.query.filter_by(id=dict_['customer_id'],
                moteur_id=user_moteur.id).first()
        assert customer.reprieve_begin != None
        assert customer.reprieve_end != None
        assert customer.ban_begin != None
        assert customer.ban_end != None

        r = self.put([{
            "reprieve_begin": None,
            "reprieve_end": None,
            "ban_begin": None,
            "ban_end": None
        }], "/customers/aa/")
        self.assert200(r)

        customer = CustomerModel.query.filter_by(id=dict_['customer_id'],
                moteur_id=user_moteur.id).first()
        assert customer.reprieve_begin == None
        assert customer.reprieve_end == None
        assert customer.ban_begin == None
        assert customer.ban_end == None

