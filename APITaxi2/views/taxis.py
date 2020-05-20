from flask import Blueprint
from flask_security import current_user, login_required, roles_accepted

from marshmallow import decorators, fields, Schema

from sqlalchemy.orm import joinedload

from APITaxi_models2 import Driver, Taxi, Vehicle, VehicleDescription

from .. import redis_backend
from ..validators import (
    data_schema_wrapper,
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('taxis', __name__)


def taxis_details_schema(taxi, taxi_operator):
    """A taxi can be registered with several operators. This function returns
    the Schema to display `taxi` registered with `operator`."""

    # Get taxi's location stored in redis.
    taxi_redis = redis_backend.get_taxi(taxi.id, taxi.added_by.email)

    class ADSSchema(Schema):
        numero = fields.String()
        insee = fields.String()

    class DriverSchema(Schema):
        professional_licence = fields.String()
        departement = fields.String(attribute='departement.numero')

    class TaxiSchema(Schema):
        id = fields.String()
        operator = fields.Constant(taxi_operator.email)
        ads = fields.Nested(ADSSchema)
        driver = fields.Nested(DriverSchema)
        rating = fields.Float()

        last_update = fields.Constant(taxi_redis.timestamp if taxi_redis else None)

        position = fields.Method('_position')

        def _position(self, _taxi):
            lon = taxi_redis.lon if taxi_redis else None
            lat = taxi_redis.lat if taxi_redis else None
            return {'lon': lon, 'lat': lat}

        # It doesn't make sense to return crowfly_distance since we don't know
        # the location of the caller. This field is returned only for backward
        # compatibility purpose.
        crowfly_distance = fields.Constant(None)

        @decorators.post_dump(pass_original=True)
        def add_vehicle_description_fields(self, data, taxi, many=False):
            """The Vehicle object linked to this Taxi may have several
            descriptions (one per operator) one of which being the one for the
            operator making the request.

            It is not easily possible to write marshmallow fields to access the
            correct description object.

            This function finds the operator's VehicleDescription object, and
            update the serialized object with fields from this object.

            See: https://github.com/marshmallow-code/marshmallow/issues/1591
            """
            for vehicle_description in taxi.vehicle.descriptions:
                if vehicle_description.added_by == taxi_operator:
                    break
            else:
                # At this point the taxi should have a description for the operator making
                # the request. If no description exists, taxis_details view
                # should have raised HTTP/404.
                raise AssertionError(
                    'No VehicleDescription of vehicle %s for operator %s' % (
                        taxi.vehicle, taxi_operator
                    )
                )

            data.update({
                'internal_id': vehicle_description.internal_id,
                'characteristics': vehicle_description.characteristics,
                'status': vehicle_description.status,
                'vehicle': {
                    'model': vehicle_description.model.name
                        if vehicle_description.model else None,
                    'constructor': vehicle_description.constructor.name
                        if vehicle_description.constructor else None,
                    'color': vehicle_description.color,
                    'licence_plate': taxi.vehicle.licence_plate,
                    'nb_seats': vehicle_description.nb_seats,
                }
            })
            return data

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
