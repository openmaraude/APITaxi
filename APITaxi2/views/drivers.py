from sqlalchemy import func
from sqlalchemy.orm import joinedload

from flask import Blueprint, request
from flask_security import current_user, login_required, roles_accepted

from APITaxi_models2 import Departement, Driver, db

from .. import schemas
from ..validators import (
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('drivers', __name__)


@blueprint.route('/drivers', methods=['POST'])
@login_required
@roles_accepted('admin', 'operateur', 'preferecture')
def drivers_create():
    schema = schemas.data_schema_wrapper(schemas.DriverSchema)()
    params, errors = validate_schema(schema, request.json)
    if errors:
        return make_error_json_response(errors)

    args = params['data'][0]

    # Query departement
    departement_query = Departement.query
    if args['departement'].get('nom'):
        departement_query = departement_query.filter(
            func.lower(Departement.nom) == args['departement'].get('nom').lower()
        )
    if args['departement'].get('numero'):
        departement_query = departement_query.filter(
            Departement.numero == args['departement'].get('numero')
        )

    departement = departement_query.one_or_none()
    if not departement:
        return make_error_json_response({
            'data': {
                '0': {
                    'departement': {
                        'nom': ['Departement not found'],
                        'numero': ['Departement not found']
                    }
                }
            }
        }, status_code=404)

    # Try to get an existing object
    driver = Driver.query.options(joinedload(Driver.departement)).filter_by(
        departement=departement,
        professional_licence=args['professional_licence']
    ).order_by(Driver.id.desc()).first()

    status_code = 200
    if not driver:
        status_code = 201
        driver = Driver(
            departement=departement,
            professional_licence=args['professional_licence'],
            added_via='api',
            added_at=func.NOW(),
            source='added_by',
            added_by=current_user
        )

    driver.first_name = args['first_name']
    driver.last_name = args['last_name']
    driver.birth_date = args.get('birth_date')

    db.session.add(driver)
    db.session.flush()

    ret = schema.dump({'data': [driver]})

    db.session.commit()

    return ret, status_code
