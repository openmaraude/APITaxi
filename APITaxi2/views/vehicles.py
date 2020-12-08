from flask import Blueprint, request
from flask_security import current_user, login_required, roles_accepted

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from APITaxi_models2 import (
    db,
    Vehicle,
    VehicleConstructor,
    VehicleModel,
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
@roles_accepted('admin', 'operateur', 'prefecture')
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
    vehicle_description = VehicleDescription.query.options(
        joinedload(VehicleDescription.model),
        joinedload(VehicleDescription.constructor)
    ).filter_by(
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

    # If model is specified in arguments, try to get the VehicleModel instance
    # or create a new one.
    if 'model' in args:
        model_name = (args['model'] or '').lower()

        if not model_name:
            vehicle_description.model = None
        else:
            vehicle_description.model = VehicleModel.query.filter(
                func.lower(VehicleModel.name) == model_name
            ).first()
            if not vehicle_description.model:
                vehicle_description.model = VehicleModel(name=model_name)
                db.session.add(vehicle_description.model)

    # If constructor is specified in arguments, try to get the
    # VehicleConstructor instance or create a new one.
    if 'constructor' in args:
        constructor_name = (args['constructor'] or '').lower()

        if not constructor_name:
            vehicle_description.constructor = None
        else:
            vehicle_description.constructor = VehicleConstructor.query.filter(
                func.lower(VehicleConstructor.name) == constructor_name
            ).first()
            if not vehicle_description.constructor:
                vehicle_description.constructor = VehicleConstructor(name=constructor_name)
                db.session.add(vehicle_description.constructor)

    # Update VehicleDescription object with the optional fields provided.
    for attr in (
        'internal_id',
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
        'nb_seats'
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
