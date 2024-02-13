from flask import Blueprint, request
import psycopg2.errors
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from APITaxi_models2 import ADS, db, Town, Vehicle, VehicleDescription

from .. import schemas
from ..security import auth, current_user
from ..validators import (
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('ads', __name__)


@blueprint.route('/ads', methods=['POST'])
@auth.login_required(role=['admin', 'operateur'])
def ads_create():
    """
    ---
    post:
      tags:
        - operator
      summary: Create a new ADS, or update the existing one (same numero & insee).
      description: |
        If the same user posts an existing tuple of (numero, insee),
        this ADS is updated instead, and the API returns 200.
      requestBody:
        content:
          application/json:
            schema: DataADSSchema
            example:
                {
                    "data": [
                        {
                            "numero": "123",
                            "insee": "75056",
                            "owner_type": "individual"
                        }
                    ]
                }
      security:
        - ApiKeyAuth: []
      responses:
        200:
          description: Return the updated ADS.
          content:
            application/json:
              schema: DataADSSchema
        201:
          description: Return the created ADS.
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
    town = Town.query.filter_by(insee=args['insee']).one_or_none()
    if not town:
        return make_error_json_response({
            'data': {
                '0': {
                    'insee': ['Unable to find town for INSEE code %s.' % args['insee']]
                }
            }
        }, status_code=404)

    # Try to get existing ADS, or create it.
    ads = ADS.query.options(joinedload(ADS.town)).filter_by(
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
            added_by=current_user,
            town=town,
        )

    ads.doublage = args.get('doublage', None)
    ads.vehicle = vehicle
    ads.category = args.get('category', '')
    ads.owner_name = args.get('owner_name', '')
    ads.owner_type = args.get('owner_type', None)

    db.session.add(ads)
    # It may happen users raise the unique contrainst despite filtering above
    # smells like a race condition if they submit twice and fast enough
    try:
        db.session.flush()
    except psycopg2.errors.UniqueViolation:
        db.session.rollback()
        return make_error_json_response({'data': {'0': {}}}, status_code=409)  # 409 Conflict

    ret = schema.dump({'data': [ads]})

    db.session.commit()

    return ret, status_code
