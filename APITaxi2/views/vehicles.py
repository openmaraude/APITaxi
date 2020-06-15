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
    schema = schemas.data_schema_wrapper(schemas.VehicleSchema)()
    params, errors = validate_schema(schema, request.json)
    if errors:
        return make_error_json_response(errors)

    args = params['data'][0]

    # Get or create Vehicle
    vehicle = Vehicle.query.filter_by(licence_plate=args['licence_plate']).one_or_none()
    if not vehicle:
        vehicle = Vehicle(licence_plate=args['licence_plate'])
        db.session.add(vehicle)

    vehicle_description = VehicleDescription.query.options(
        joinedload(VehicleDescription.model),
        joinedload(VehicleDescription.constructor),
    ).filter_by(
        vehicle=vehicle,
        added_by=current_user
    ).one_or_none()

    if not vehicle_description:
        # Get or create VehicleModel
        model_name = args.get('model', '').lower()
        model = None
        if model_name:
            model = VehicleModel.query.filter(
                func.lower(VehicleModel.name) == model_name
            ).first()
            if not model:
                model = VehicleModel(name=model_name)
                db.session.add(model)

        # Get or create VehicleConstructor
        constructor_name = args.get('constructor', '').lower()
        constructor = None
        if constructor_name:
            constructor = VehicleConstructor.query.filter(
                func.lower(VehicleConstructor.name) == constructor_name
            ).first()
            if not constructor:
                constructor = VehicleConstructor(name=constructor_name)
                db.session.add(constructor)

        vehicle_description = VehicleDescription(
            model=model,
            constructor=constructor,
            vehicle=vehicle,

            internal_id=args.get('internal_id'),
            model_year=args.get('model_year'),
            engine=args.get('engine'),
            horse_power=args.get('horse_power'),
            relais=args.get('relais'),
            horodateur=args.get('horodateur'),
            taximetre=args.get('taximetre'),
            date_dernier_ct=args.get('date_dernier_ct'),
            date_validite_ct=args.get('date_validite_ct'),
            special_need_vehicle=args.get('special_need_vehicle'),
            type=args.get('type_'),
            luxury=args.get('luxury'),
            credit_card_accepted=args.get('credit_card_accepted'),
            nfc_cc_accepted=args.get('nfc_cc_accepted'),
            amex_accepted=args.get('amex_accepted'),
            bank_check_accepted=args.get('bank_check_accepted'),
            fresh_drink=args.get('fresh_drink'),
            dvd_player=args.get('dvd_player'),
            tablet=args.get('tablet'),
            wifi=args.get('wifi'),
            baby_seat=args.get('baby_seat'),
            bike_accepted=args.get('bike_accepted'),
            pet_accepted=args.get('pet_accepted'),
            air_con=args.get('air_con'),
            electronic_toll=args.get('electronic_toll'),
            gps=args.get('gps'),
            cpam_conventionne=args.get('cpam_conventionne'),
            every_destination=args.get('every_destination'),
            color=args.get('color'),
            nb_seats=args.get('nb_seats'),
            status='off',

            added_by=current_user,
            added_via='api',
            added_at=func.NOW(),
            source='added_by'
        )
        db.session.add(vehicle_description)

    ret = schema.dump({'data': [(vehicle, vehicle_description)]})

    db.session.commit()

    return ret
