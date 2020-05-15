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


def _get_vehicle_desc(vehicle, operator, fields):
    """A Vehicle can be registered by several operators. This function
    retrieves the vehicle description for `operator`, and returns the attribute
    as specified by `fields`.

    For example the call:

    >>> _get_vehicle_desc(vehicle, operator, 'model.name')

    retrieves the vehicle description registered by "operator", and returns the
    `name` of the `model` attribute.
    """
    for description in vehicle.descriptions:
        if description.added_by == operator:
            break
    else:
        raise AssertionError('No VehicleDescription of vehicle %s for operator %s' % (vehicle, operator))

    ret = description
    for part in fields.split('.'):
        if not ret:
            return None
        ret = getattr(ret, part)
    return ret


def taxis_details_schema(taxi, taxi_operator):
    """A taxi can be registered with several operators. This function returns
    the Schema to display `taxi` registered with `operator`."""
    taxi_redis = redis_backend.get_taxi(taxi.id, taxi.added_by.email)

    class PowerSchema(Schema):
        def get_attribute(self, obj, attr, default):
            """Extend Schema to accept when fields.attribute is a lambda.

            See https://github.com/marshmallow-code/marshmallow/issues/1591
            """
            if callable(attr):
                return attr(obj)
            return super().get_attribute(obj, attr, default)

    class VehicleSchema(PowerSchema):
        model = fields.String(
            attribute=lambda vehicle: _get_vehicle_desc(vehicle, taxi_operator, 'model.name')
        )
        constructor = fields.String(
            attribute=lambda vehicle: _get_vehicle_desc(vehicle, taxi_operator, 'constructor.name')
        )
        color = fields.String(
            attribute=lambda vehicle: _get_vehicle_desc(vehicle, taxi_operator, 'color')
        )
        licence_plate = fields.String()

        nb_seats = fields.String(
            attribute=lambda vehicle: _get_vehicle_desc(vehicle, taxi_operator, 'nb_seats')
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
            attribute=lambda taxi: _get_vehicle_desc(taxi.vehicle, taxi_operator, 'internal_id')
        )
        operator = fields.Constant(taxi_operator.email)
        vehicle = fields.Nested(VehicleSchema)
        ads = fields.Nested(ADSSchema)
        driver = fields.Nested(DriverSchema)
        characteristics = fields.List(
            fields.String,
            attribute=lambda taxi: _get_vehicle_desc(taxi.vehicle, taxi_operator, 'characteristics')
        )
        rating = fields.Float()

        status = fields.String(
            attribute=lambda taxi: _get_vehicle_desc(taxi.vehicle, taxi_operator, 'status')
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
        joinedload(Taxi.vehicle)
        .joinedload(Vehicle.descriptions)
        .joinedload(VehicleDescription.added_by)
    ).options(
        joinedload(Taxi.added_by)
    ).filter(
        Taxi.id == taxi_id,
        # Make sure a VehicleDescription exists for the vehicle.
        # taxi.vehicle.descriptions will contain the vehicle descriptions of
        # all operators, not only the one added by the current user.
        VehicleDescription.added_by == current_user
    )

    taxi = query.one_or_none()

    if not taxi:
        return make_error_json_response({
            'url': 'Unknown taxi %s, or taxi exists but you are not the owner.' % taxi_id
        }, status_code=404)

    schema = taxis_details_schema(taxi, current_user)()

    return schema.dump({'data': [taxi]})
