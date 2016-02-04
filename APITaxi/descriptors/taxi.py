# -*- coding: utf-8 -*-
from ..models import taxis as taxis_models, administrative as administrative_models
from ..api import api
from ..utils import fields
from .common import coordinates_descriptor

vehicle_descriptor = api.model('vehicle_descriptor',
    {
        "model": fields.String,
        "constructor": fields.String,
        "color": fields.String(),
        "licence_plate": fields.String,
        "characteristics": fields.List(fields.String),
        "nb_seats": fields.Integer
    })
ads_descriptor = api.model('ads_descriptor', {
        "numero": fields.String,
        "insee": fields.String
})
driver_descriptor = api.model('driver_descriptor', {
        'professional_licence': fields.String,
        'departement': fields.String
})
taxi_descriptor = api.model('taxi_descriptor',
    {
        "id": fields.String,
        "operator": fields.String,
        "position": fields.Nested(coordinates_descriptor),
        "vehicle": fields.Nested(vehicle_descriptor, required=True),
        "last_update": fields.Integer,
        "crowfly_distance": fields.Float,
        "ads": fields.Nested(ads_descriptor, required=True),
        "driver": fields.Nested(driver_descriptor, required=True),
        "status": fields.String,
        "rating": fields.Float
    })

taxi_model_details = api.model('taxi_model_details',
         {'vehicle_licence_plate': fields.String,
          'ads_numero': fields.String,
          'ads_insee': fields.String,
          'driver_professional_licence': fields.String,
          'driver_departement': fields.String,
           'id': fields.String})

taxi_model = api.model('taxi_model',
                 {'data': fields.List(
                     fields.Nested(taxi_descriptor),
                     unique=True)})

authorized_taxi_statuses = ['free', 'occupied', 'oncoming', 'off']
dict_taxi_expect = \
     {'vehicle': fields.Nested(api.model('vehicle_expect',
            {'licence_plate': fields.String}), required=True),
          'ads': fields.Nested(api.model('ads_expect',
              {'numero': fields.String, 'insee': fields.String}), required=True),
          'driver': fields.Nested(api.model('driver_expect',
              {'professional_licence': fields.String,
                'departement': fields.String}), required=True),
          'status': fields.String(enum=authorized_taxi_statuses),
          'id': fields.String(required=False)
         }

taxi_model_expect = api.model('taxi_expect',
              {'data':fields.List(
                  fields.Nested(api.model('taxi_expect_details', dict_taxi_expect)),
                  unique=True)})

taxi_put_expect = api.model('taxi_put_expect',
  {'data': fields.List(fields.Nested(api.model('api_expect_status',
   {'status': fields.String(required=True, enum=authorized_taxi_statuses)
})), unique=True)})
