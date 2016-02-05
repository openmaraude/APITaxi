#coding: utf-8
from ..api import api
from ..models.vehicle import Vehicle
from APITaxi_utils import fields

vehicle_model = api.model('vehicle_model_data',
    {'data': fields.List(fields.Nested(
        api.model('vehicle_model', Vehicle.marshall_obj(api=api))
        ))
    }
)

vehicle_expect = api.model('vehicle_expect_data',
    {'data': fields.List(fields.Nested(
        api.model('vehicle_expect', Vehicle.marshall_obj(
            filter_id=True, api=api))
        ))
    }
)
