from flask import Blueprint, request
from flask_security import current_user, login_required, roles_accepted

from sqlalchemy import func

from APITaxi_models2 import (
    db,
    Vehicle,
    VehicleDescription,
)

from .. import schemas
from ..validators import (
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('vehicles', __name__)


@blueprint.route('/vehicles', methods=['POST'])
@login_required
@roles_accepted('admin', 'operateur')
def vehicle_create():
    """
    ---
    post:
      description: |
        Create a new vehicle.
      requestBody:
        content:
          application/json:
            schema: DataVehicleSchema
      security:
        - ApiKeyAuth: []
      responses:
        200:
          description: Return and update the existing ressource.
          content:
            application/json:
              schema: DataVehicleSchema
        201:
          description: Return a new ressource.
    """
    schema = schemas.DataVehicleSchema()
    params, errors = validate_schema(schema, request.json)
    if errors:
        return make_error_json_response(errors)

    args = params['data'][0]

    # Get or create Vehicle
    vehicle = Vehicle.query.filter_by(licence_plate=args['licence_plate']).one_or_none()
    if not vehicle:
        vehicle = Vehicle(licence_plate=args['licence_plate'])
        db.session.add(vehicle)

    # Get or create VehicleDescription.
    vehicle_description = VehicleDescription.query.filter_by(
        vehicle=vehicle,
        added_by=current_user
    ).one_or_none()

    if vehicle_description:
        http_code = 200
    else:
        http_code = 201
        vehicle_description = VehicleDescription(
            vehicle=vehicle,
            status='off',
            added_by=current_user,
            added_via='api',
            added_at=func.NOW(),
            source='added_by'
        )
        db.session.add(vehicle_description)

    # Update VehicleDescription object with the optional fields provided.
    for attr in (
        'model_year',
        'engine',
        'horse_power',
        'relais',
        'horodateur',
        'taximetre',
        'date_dernier_ct',
        'date_validite_ct',
        'special_need_vehicle',
        ('type', 'type_'),
        'luxury',
        'credit_card_accepted',
        'nfc_cc_accepted',
        'amex_accepted',
        'bank_check_accepted',
        'fresh_drink',
        'dvd_player',
        'tablet',
        'wifi',
        'baby_seat',
        'bike_accepted',
        'pet_accepted',
        'air_con',
        'electronic_toll',
        'gps',
        'cpam_conventionne',
        'every_destination',
        'color',
        'nb_seats',
        'model',
        'constructor'
    ):
        try:
            model_name, arg_name = attr
        except ValueError:
            model_name, arg_name = attr, attr

        if arg_name in args:
            setattr(vehicle_description, model_name, args[arg_name])

    ret = schema.dump({'data': [(vehicle, vehicle_description)]})

    db.session.commit()

    return ret, http_code
