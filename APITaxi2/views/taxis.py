from flask import Blueprint, request
from flask_security import current_user, login_required, roles_accepted

from marshmallow import decorators, fields, Schema, validate

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from APITaxi_models2 import (
    ADS,
    db,
    Departement,
    Driver,
    Taxi,
    Vehicle,
    VehicleDescription,
)
from APITaxi_models2.vehicle import UPDATABLE_VEHICLE_STATUS

from .. import redis_backend
from ..utils import get_short_uuid
from ..validators import (
    data_schema_wrapper,
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('taxis', __name__)


def _find_operator_vehicle_description(vehicle, operator):
    """For a given Vehicle can exist several VehicleDescription objects, one
    for each operator.

    This function returns the VehicleDescription of `vehicle` for `operator`.
    """
    for vehicle_description in vehicle.descriptions:
        if vehicle_description.added_by == operator:
            return vehicle_description
    return None


def taxis_details_schema(taxi_operator, taxi_redis=None):
    class ADSSchema(Schema):
        numero = fields.String(required=True, allow_none=False)
        insee = fields.String(required=True, allow_none=False)

    class ADSSchema(Schema):
        numero = fields.String(required=True, allow_none=False)
        insee = fields.String(required=True, allow_none=False)

    class DriverSchema(Schema):
        professional_licence = fields.String(required=True, allow_none=False)
        departement = fields.String(attribute='departement.numero')

    class VehicleSchema(Schema):
        model = fields.String(required=False, allow_none=True)
        constructor = fields.String(required=False, allow_none=True)
        color = fields.String(required=False, allow_none=True)
        licence_plate = fields.String(required=True, allow_none=False)
        nb_seats = fields.Int(required=False, allow_none=True)

    class PositionSchema(Schema):
        lon = fields.Float(required=True, allow_none=True)
        lat = fields.Float(required=True, allow_none=True)

    class TaxiSchema(Schema):
        id = fields.String()
        internal_id = fields.String(allow_none=True)
        operator = fields.String(required=False, allow_none=False)
        vehicle = fields.Nested(VehicleSchema, required=True)
        ads = fields.Nested(ADSSchema, required=True)
        driver = fields.Nested(DriverSchema, required=True)
        characteristics = fields.List(fields.String, required=False, allow_none=False)
        rating = fields.Float(required=False, allow_none=False)

        status = fields.String(
            required=False, allow_none=False,
            validate=validate.OneOf(UPDATABLE_VEHICLE_STATUS)
        )

        # For backward compatibility, last_update is the timestamp of the last
        # position update, stored in redis, and not the last taxi object
        # modification.
        last_update = fields.Constant(
            taxi_redis.timestamp if taxi_redis else None,
            required=False, allow_none=False
        )

        position = fields.Nested(PositionSchema, required=False, allow_none=False)

        # It doesn't make sense to return crowfly_distance since we don't know
        # the location of the caller. This field is returned for backward
        # compatibility.
        crowfly_distance = fields.Constant(None, required=False, allow_none=True)

        @decorators.post_dump(pass_original=True)
        def _add_fields(self, data, taxi, many=False):
            """Extend output with vehicle_description details, and position
            from redis.
            """
            vehicle_description = _find_operator_vehicle_description(taxi.vehicle, taxi_operator)
            # Should never happen. We should make sure the VehicleDescription exists
            # before attempting to dump the object.
            if not vehicle_description:
                raise RuntimeError('Taxi %s does not have a vehicle.description object for user %s' % (taxi, taxi_operator))

            data.update({
                'operator': vehicle_description.added_by.email,
                'internal_id': vehicle_description.internal_id,
                'characteristics': vehicle_description.characteristics,
                'status': vehicle_description.status,
                'position': {
                    'lon': taxi_redis.lon if taxi_redis else None,
                    'lat': taxi_redis.lat if taxi_redis else None,
                }
            })
            data['vehicle'].update({
                'model': vehicle_description.model.name
                    if vehicle_description.model else None,
                'constructor': vehicle_description.constructor.name
                    if vehicle_description.constructor else None,
                'color': vehicle_description.color,
                'nb_seats': vehicle_description.nb_seats,
            })
            return data

    return data_schema_wrapper(TaxiSchema)


@blueprint.route('/taxis', methods=['POST'])
@login_required
@roles_accepted('admin', 'operateur')
def taxis_create():
    """Endpoint POST /taxis to create Taxi object. If the taxi already exists, which is
    defined as the combination of an ads, a vehicle and a driver, it is
    returned instead of being created.
    """
    schema = taxis_details_schema(
        current_user
    )()

    params, errors = validate_schema(schema, request.json)
    if errors:
        return make_error_json_response(errors)

    args = params['data'][0]

    errors = {}
    ads = ADS.query.filter_by(insee=args['ads']['insee'],
                              numero=args['ads']['numero']).one_or_none()
    if not ads:
        errors['ads'] = {
            'insee': ['ADS not found with this INSEE/numero'],
            'numero': ['ADS not found with this INSEE/numero']
        }

    vehicle = Vehicle.query.options(joinedload('*')).filter_by(
        licence_plate=args['vehicle']['licence_plate']
    ).one_or_none()
    if not vehicle:
        errors['vehicle'] = {
            'licence_plate': ['Invalid licence plate']
        }
    elif not _find_operator_vehicle_description(vehicle, current_user):
        errors['vehicle'] = {
            'licence_plate': ['Vehicle exists but has not been created by the user making the request']
        }

    departement = Departement.query.filter_by(
        numero=args['driver']['departement']['numero']
    ).one_or_none()
    if not departement:
        errors['driver'] = {
            'departement': ['Departement not found']
        }

    driver = Driver.query.options(joinedload('*')).filter_by(
        professional_licence=args['driver']['professional_licence'],
        departement=departement
    ).one_or_none()
    if not driver:
        if 'driver' not in errors:
            errors['driver'] = {}
        errors['driver'].update({
            'professional_licence': ['Driver not found with this professional_licence. Is it the correct departement?'],
        })

    if errors:
        return make_error_json_response({
            'data': {'0': errors}
        }, status_code=404)

    # Try to get existing Taxi, or create it.
    taxi = Taxi.query.options(joinedload('*')).filter_by(
        ads=ads,
        driver=driver,
        vehicle=vehicle,
    ).one_or_none()

    status_code = 200

    if not taxi:
        status_code = 201
        taxi = Taxi(
            id=get_short_uuid(),
            vehicle=vehicle,
            ads=ads,
            added_by=current_user,
            driver=driver,
            added_via='api',
            added_at=func.NOW(),
            source='added_by',
        )
        db.session.add(taxi)
        db.session.flush()

    ret = schema.dump({'data': [taxi]})

    db.session.commit()

    return ret, status_code


@blueprint.route('/taxis/<string:taxi_id>', methods=['GET', 'PUT'])
@login_required
@roles_accepted('admin', 'operateur')
def taxis_details(taxi_id):
    # Get Taxi object with the VehicleDescription entry related to current
    # user.
    query = db.session.query(Taxi, VehicleDescription).options(
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
    ).options(
        joinedload(Taxi.current_hail)
    ).filter(
        VehicleDescription.vehicle_id == Taxi.vehicle_id
    ).filter(
        Taxi.id == taxi_id,
        VehicleDescription.added_by == current_user
    )

    res = query.one_or_none()
    if not res:
        return make_error_json_response({
            'url': 'Unknown taxi %s, or taxi exists but you are not the owner.' % taxi_id
        }, status_code=404)
    taxi, vehicle_description = (res.Taxi, res.VehicleDescription)

    # Build Schema
    schema = taxis_details_schema(
        current_user,
        redis_backend.get_taxi(taxi.id, taxi.added_by.email),
    )()

    # Dump data for GET requests
    if request.method != 'PUT':
        return schema.dump({'data': [taxi]})

    params, errors = validate_schema(schema, request.json, partial=True)
    if errors:
        return make_error_json_response(errors)

    args = request.json['data'][0]

    # For now it is only possible to update the taxi's status. In the future,
    # We should allow the edition of other fields (taxi.internal_id, ...).
    if 'status' in args and args['status'] != vehicle_description.status:
        taxi.last_update_at = func.now()
        vehicle_description.last_update_at = func.now()
        vehicle_description.status = args['status']

        # If there is a current hail, and the taxi changes it's status to
        # "occupied" when he previously accepted a hail, we assume the customer
        # is now on board.
        if (taxi.current_hail
                and args['status'] == 'occupied'
                and taxi.current_hail.status == 'accepted_by_customer'
        ):
            taxi.current_hail.status = 'customer_on_board'

        # If there is a current hail, and the taxi changes it's status to
        # "free" or "off" during a trip, we assume the trip is finished.
        if (taxi.current_hail
                and args['status'] in ('free', 'off')
                and taxi.current_hail.status == 'customer_on_board'
        ):
            taxi.current_hail.status = 'finished'

        redis_backend.set_taxi_availability(
            taxi_id,
            vehicle_description.added_by,
            vehicle_description.status == 'free'
        )

        # Store history
        redis_backend.log_taxi_status(
            taxi_id,
            args['status']
        )

        db.session.flush()

    output = schema.dump({'data': [taxi]})

    db.session.commit()

    return output
