# -*- coding: utf-8 -*-
from APITaxi_models.hail import Hail as HailModel
from ..api import api
from APITaxi_utils import fields
from .common import coordinates_descriptor
from copy import deepcopy

all_fields = HailModel.marshall_obj(api=api)
all_fields['operateur'] = fields.String(attribute='operateur.email',
        required=True)
all_fields['id'] = fields.String()
all_fields['taxi'] = fields.Nested(api.model('hail_taxi',
        {'position': fields.Nested(coordinates_descriptor),
         'last_update': fields.Integer(),
         'id': fields.String()}))
all_fields['creation_datetime'] = fields.DateTime()
all_fields['customer_id'] = fields.String(required=True)

hail_model = api.model('hail_model_data',
    {'data':
        fields.List(fields.Nested(
            api.model('hail_model', all_fields))
    )}
)

puttable_arguments = ['status', 'incident_taxi_reason',
        'reporting_customer', 'reporting_customer_reason', 'customer_lon',
        'customer_lat', 'customer_address', 'customer_phone_number', 'rating_ride',
        'rating_ride_reason', 'incident_customer_reason']

dict_hail =  dict([f for f in list(all_fields.items()) if f[0] in puttable_arguments])

postable_arguments = ['customer_id', 'customer_lon', 'customer_lat',
    'customer_address', 'customer_phone_number', 'taxi_id', 'operateur', 'session_id']
dict_hail =  dict([f for f in list(all_fields.items()) if f[0] in postable_arguments])
dict_hail['operateur'] = fields.String(attribute='operateur', required=True)
dict_hail['taxi_id'] = fields.String(required=True)
hail_expect_post_details = api.model('hail_expect_post_details',
        deepcopy(dict_hail))
hail_expect_post = api.model('hail_expect_post',
        {'data': fields.List(fields.Nested(hail_expect_post_details),
            unique=True)})

dict_put = deepcopy(dict_hail)
for k in list(dict_put.keys()):
    dict_put[k].required = False

hail_expect_put_details = api.model('hail_expect_put_details', dict_put)
hail_expect_put = api.model('hail_expect_put',
        {'data': fields.List(fields.Nested(hail_expect_put_details),
            unique=True)})
