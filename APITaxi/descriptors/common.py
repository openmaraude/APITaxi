# -*- coding: utf-8 -*-
from ..api import api
from APITaxi_utils import fields
coordinates_descriptor = api.model('coordinates_descriptor',
        {"lon": fields.Float, "lat": fields.Float})
