# -*- coding: utf-8 -*-
from ..api import api
from ..utils import fields
coordinates_descriptor = api.model('coordinates_descriptor',
        {"lon": fields.Float, "lat": fields.Float})
