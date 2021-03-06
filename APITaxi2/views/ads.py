from sqlalchemy import func

from flask import Blueprint, request

from flask_security import current_user, login_required, roles_accepted

from APITaxi_models2 import ADS, db, Vehicle, VehicleDescription, ZUPC

from .. import schemas
from ..validators import (
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('ads', __name__)


@blueprint.route('/ads', methods=['POST'])
@login_required
@roles_accepted('admin', 'operateur')
def ads_create():
    """
    ---
    post:
      description: |
        Create a new ADS.
      requestBody:
        content:
          application/json:
            schema: DataADSSchema
      security:
        - ApiKeyAuth: []
      responses:
        200:
          description: Return the already existing ADS.
          content:
            application/json:
              schema: DataADSSchema
        201:
          description: Create a new ADS.
    """
    schema = schemas.DataADSSchema()
    params, errors = validate_schema(schema, request.json)
    if errors:
        return make_error_json_response(errors)

    args = params['data'][0]

    # Vehicle is optional, but if it is provided it must be valid.
    vehicle = None
    if args.get('vehicle_id') is not None:
        vehicle = Vehicle.query.join(VehicleDescription).filter(
            Vehicle.id == args['vehicle_id'],
            VehicleDescription.added_by == current_user
        ).one_or_none()
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
        insee=args['insee'],
        added_by=current_user
    ).order_by(ADS.id.desc()).first()

    status_code = 200
    if not ads:
        status_code = 201
        ads = ADS(
            numero=args['numero'],
            insee=args['insee'],
            added_via='api',
            added_at=func.NOW(),
            source='added_by',
            added_by=current_user
        )

    ads.doublage = args.get('doublage', None)
    ads.vehicle = vehicle
    ads.category = args.get('category', '')
    ads.owner_name = args.get('owner_name', '')
    ads.owner_type = args.get('owner_type', None)
    ads.zupc = zupc

    db.session.add(ads)
    db.session.flush()

    ret = schema.dump({'data': [ads]})

    db.session.commit()

    return ret, status_code
