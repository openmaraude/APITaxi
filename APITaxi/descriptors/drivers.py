#coding: utf-8
from ..api import api
from APITaxi_models import Driver
from APITaxi_utils import fields

driver_fields = api.model('driver_fields_data',
    {'data': fields.List(fields.Nested(
        api.model('driver_fields', Driver.marshall_obj(api=api))
        ))
    }
)

driver_details_expect = api.model('driver_expect_data',
    {'data': fields.List(fields.Nested(
        api.model('driver_expect', Driver.marshall_obj(filter_id=True, api=api))
        ))
    }
)
