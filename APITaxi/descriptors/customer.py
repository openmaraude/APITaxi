#coding: utf-8
from APITaxi_utils import fields
from ..api import api

customer_fields = api.model('customer_model',
                    {'customer_id': fields.String,
                     'moteur_id': fields.String,
                     'reprieve_begin': fields.String,
                     'reprieve_end': fields.String,
                     'ban_begin': fields.String,
                     'ban_end': fields.String,
                    })
customer_model = api.model('customer_model_data',
    {'data': fields.List(fields.Nested(
            customer_fields))
    }
)
