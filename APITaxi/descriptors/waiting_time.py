# -*- coding: utf-8 -*-
from ..api import api
from APITaxi_utils import fields

waiting_time_model = api.model('waiting_time_descriptor',
    {
        "timestamp": fields.String(),
        "waiting_time": fields.Integer()
    }
)

waiting_time_response = api.model('waiting_time_response',
{"data": fields.List(fields.Nested(waiting_time_model))})