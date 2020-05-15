from flask import Blueprint
from flask_security import current_user, login_required, roles_accepted

from marshmallow import fields, Schema

from sqlalchemy.orm import joinedload

from APITaxi_models2 import Driver, Taxi, Vehicle, VehicleDescription

from .. import redis_backend
from ..validators import (
    data_schema_wrapper,
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('taxis', __name__)


def _get_vehicle_description(vehicle, fields):
    """Helper to get an attribute of the taxi description. For example to
    retrieve vehicle.descriptions[0].model.name:

    >>> _get_vehicle_description(vehicle, 'model.name')

    We assume vehicle.descriptions is a list of at most one element since there
    is at most one description for each operator.
    """
    if not vehicle or not vehicle.descriptions:
        return None

    ret = vehicle.descriptions[0]
    for part in fields.split('.'):
        if not ret:
            return None
        ret = getattr(ret, part)
    return ret


def taxis_details_schema(taxi):
    taxi_redis = redis_backend.get_taxi(taxi.id, taxi.added_by.email)

    class PowerSchema(Schema):
        def get_attribute(self, obj, attr, default):
            """Handle when fields.attribute is a lambda.

            Taxi.vehicle.descriptions is a list and we only want to expose data
            stored in the first element of this list. There is no easy way to
            do it with marshmallow so we use _get_vehicle_description().

            See https://github.com/marshmallow-code/marshmallow/issues/1591
            """
            if callable(attr):
                return attr(obj)
            return super().get_attribute(obj, attr, default)

    class VehicleSchema(PowerSchema):
        model = fields.String(
            attribute=lambda vehicle: _get_vehicle_description(vehicle, 'model.name')
        )
        constructor = fields.String(
            attribute=lambda vehicle: _get_vehicle_description(vehicle, 'constructor.name')
        )
        color = fields.String(
            attribute=lambda vehicle: _get_vehicle_description(vehicle, 'color')
        )
        licence_plate = fields.String()

        nb_seats = fields.String(
            attribute=lambda vehicle: _get_vehicle_description(vehicle, 'nb_seats')
        )

    class ADSSchema(Schema):
        numero = fields.String()
        insee = fields.String()

    class DriverSchema(Schema):
        professional_licence = fields.String()
        departement = fields.String(attribute='departement.numero')

    class TaxiSchema(PowerSchema):
        id = fields.String()
        internal_id = fields.String(
            attribute=lambda taxi: _get_vehicle_description(taxi.vehicle, 'internal_id')
        )
        operator = fields.String(
            attribute=lambda taxi: taxi.added_by.email
        )
        vehicle = fields.Nested(VehicleSchema)
        ads = fields.Nested(ADSSchema)
        driver = fields.Nested(DriverSchema)
        characteristics = fields.List(
            fields.String,
            attribute=lambda taxi: _get_vehicle_description(taxi.vehicle, 'characteristics')
        )
        rating = fields.Float()

        status = fields.String(
            attribute=lambda taxi: _get_vehicle_description(taxi.vehicle, 'status')
        )
        last_update = fields.Constant(taxi_redis.timestamp if taxi_redis else None)

        position = fields.Method('_position')

        def _position(self, taxi):
            lon = taxi_redis.lon if taxi_redis else None
            lat = taxi_redis.lat if taxi_redis else None
            return {'lon': lon, 'lat': lat}

        # It doesn't make sense to return crowfly_distance since we don't know
        # the location of the caller. This field is returned only for backward
        # compatibility purpose.
        crowfly_distance = fields.Constant(None)

    return data_schema_wrapper(TaxiSchema)


@blueprint.route('/taxis/<string:taxi_id>', methods=['GET'])
@login_required
@roles_accepted('admin', 'operateur')
def taxis_details(taxi_id):
    query = Taxi.query.options(
        joinedload(Taxi.ads)
    ).options(
        joinedload(Taxi.driver)
        .joinedload(Driver.departement)
    ).options(
        joinedload(Taxi.vehicle)
        .joinedload(Vehicle.descriptions)
        .joinedload(VehicleDescription.constructor)
    ).options(
        joinedload(Taxi.vehicle)
        .joinedload(Vehicle.descriptions)
        .joinedload(VehicleDescription.model)
    ).options(
        joinedload(Taxi.added_by)
    ).filter(
        Taxi.id == taxi_id,
        VehicleDescription.added_by == current_user
    )

    # In database a Vehicle can have at most one VehicleDescription for each
    # operator so this request can't return more than 1 result.
    # We should probably make it possible for administrators to select the
    # taxi's operator.
    taxi = query.one_or_none()

    if not taxi:
        return make_error_json_response({
            'url': 'Unknown taxi %s, or taxi exists but you are not the owner.' % taxi_id
        }, status_code=404)

    schema = taxis_details_schema(taxi)()

    return schema.dump({'data': [taxi]})
