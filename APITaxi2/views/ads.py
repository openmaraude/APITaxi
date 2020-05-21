from sqlalchemy import func

from flask import Blueprint, request

from flask_security import current_user, login_required, roles_accepted

from marshmallow import fields, validate, Schema

from APITaxi_models2 import ADS, db, Vehicle, ZUPC

from ..validators import (
    data_schema_wrapper,
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('ads', __name__)


def ads_create_schema():
    class ADSSchema(Schema):
        category = fields.String(required=True)
        vehicle_id = fields.Int(allow_none=True)
        insee = fields.String(required=True)
        numero = fields.String(required=True)
        owner_name = fields.String(required=True)
        owner_type = fields.String(
            required=True,
            validate=validate.OneOf(['individual', 'company'])
        )
        doublage = fields.Bool()

    return data_schema_wrapper(ADSSchema)


@blueprint.route('/ads', methods=['POST'])
@login_required
@roles_accepted('admin', 'operateur')
def ads_create():
    schema = ads_create_schema()()
    params, errors = validate_schema(schema, request.json)
    if errors:
        return make_error_json_response(errors)

    args = params['data'][0]

    # Vehicle is optional, but if it is provided it must be valid.
    vehicle = None
    if args.get('vehicle_id') is not None:
        vehicle = Vehicle.query.filter_by(id=args['vehicle_id']).one_or_none()
        if not vehicle:
            return make_error_json_response({
                'data': {
                    '0': {
                        'vehicle_id': ['Unable to find vehicle %s.' % args['vehicle_id']]
                    }
                }
            }, status_code=404)

    # Check if INSEE is valid.
    zupc = ZUPC.query.filter_by(insee=args['insee']).one_or_none()
    if not zupc:
        return make_error_json_response({
            'data': {
                '0': {
                    'insee': ['Unable to find ZUPC for INSEE code %s.' % args['insee']]
                }
            }
        }, status_code=404)

    # Try to get existing ADS, or create it.
    ads = ADS.query.filter_by(
        numero=args['numero'],
        insee=args['insee']
    ).one_or_none()

    if not ads:
        ads = ADS(
            numero=args['numero'],
            insee=args['insee'],
            added_via='api',
            added_at=func.NOW(),
            source='added_by',
            added_by=current_user
        )

    # By default, doublage is false for backward compatibility but we should
    # probably set it to NULL if it is not provided.
    # Anyway, we should also consider removing the parameter completely. We
    # don't really need this value.
    ads.doublage = args.get('doublage', False)
    ads.vehicle = vehicle
    ads.category = args['category']
    ads.owner_name = args['owner_name']
    ads.owner_type = args['owner_type']
    ads.zupc = zupc

    db.session.add(ads)
    db.session.flush()

    ret = schema.dump({'data': [ads]})

    db.session.commit()

    return ret
