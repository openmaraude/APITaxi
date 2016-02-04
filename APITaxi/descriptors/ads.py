#coding: utf-8
from APITaxi_utils import fields
from ..api import api
from ..models.taxis import ADS

ads_model = api.model('ADS_model_data',
    {'data': fields.List(fields.Nested(
            api.model('ADS_model', ADS.marshall_obj())))
    }
)


ads_expect = api.model('ADS_expect_data',
    {'data': fields.List(fields.Nested(
        api.model('ADS_expect', ADS.marshall_obj(show_all=True, filter_id=True))
        ))
    }
)

ads_post = api.model('ADS_post_data',
    {'data': fields.List(fields.Nested(
            api.model('ADS_post', ADS.marshall_obj(show_all=True))
        ))
    }
)
