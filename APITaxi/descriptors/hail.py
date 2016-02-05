# -*- coding: utf-8 -*-
from ..models.hail import Hail as HailModel
from ..api import api
from APITaxi_utils import fields

all_fields = HailModel.marshall_obj(api=api)

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

dict_hail =  dict(filter(lambda f: f[0] in puttable_arguments,
        all_fields.items()))
for k in dict_hail.keys():
    dict_hail[k].required = False

hail_expect_put_details = api.model('hail_expect_put_details', dict_hail)
hail_expect_put = api.model('hail_expect_put',
        {'data': fields.List(fields.Nested(hail_expect_put_details),
            unique=True)})

postable_arguemnts = ['customer_id', 'customer_lon', 'customer_lat',
    'customer_address', 'customer_phone_number', 'taxi_id', 'operateur']
dict_hail =  dict(filter(lambda f: f[0] in postable_arguemnts,
        HailModel.marshall_obj(api=api).items()))
dict_hail['operateur'] = fields.String(attribute='operateur.email', required=True)
dict_hail['taxi_id'] = fields.String(required=True)
hail_expect_post_details = api.model('hail_expect_post_details', dict_hail)
hail_expect_post = api.model('hail_expect_post',
        {'data': fields.List(fields.Nested(hail_expect_post_details),
            unique=True)})
