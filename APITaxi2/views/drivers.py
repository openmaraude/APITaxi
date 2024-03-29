from flask import Blueprint, request
import psycopg2.errors
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from APITaxi_models2 import Departement, Driver, db

from .. import schemas
from ..security import auth, current_user
from ..validators import (
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('drivers', __name__)


@blueprint.route('/drivers', methods=['POST'])
@auth.login_required(role=['admin', 'operateur'])
def drivers_create():
    """
    ---
    post:
      tags:
        - operator
      summary: Create a new driver, or update an existing one (same departement & professional licence).
      description: |
        If the same user posts an existing tuple of (departement, professional_licence),
        this driver is updated instead, and the API returns 200.

        The departement is where the professional licence was delivered.
        The departement can be specified by name or number, we encourage users to use the number only.
      requestBody:
        content:
          application/json:
            schema: DataDriverSchema
            example:
                {
                    "data": [
                        {
                            "first_name": "Francette",
                            "last_name": "Moulin",
                            "birth_date": "1970-12-05",
                            "professional_licence": "foobar-994468249464",
                            "departement": {
                                "numero": "76"
                            }
                        }
                    ]
                }
      security:
        - ApiKeyAuth: []
      responses:
        200:
          description: Return the updated driver.
          content:
            application/json:
              schema: DataDriverSchema
        201:
          description: Return the created driver.
    """
    schema = schemas.DataDriverSchema()
    params, errors = validate_schema(schema, request.json)
    if errors:
        return make_error_json_response(errors)

    args = params['data'][0]

    # Query departement. We allow to specify both "nom" and "numero", but some
    # clients make requests with spelling mistakes so we accept even if only
    # one of the two is valid.
    departement_filters = []
    if args['departement'].get('nom'):
        departement_filters.append(
            func.lower(Departement.nom) == args['departement'].get('nom').lower()
        )
    if args['departement'].get('numero'):
        departement_filters.append(
            Departement.numero == args['departement'].get('numero')
        )

    departements = Departement.query.filter(or_(*departement_filters)).all()

    if not departements:
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
    elif len(departements) > 1:
        return make_error_json_response({
            'data': {
                '0': {
                    'departement': {
                        'nom': ['There is more than one match for this nom/numero'],
                        'numero': ['There is more than one match for this nom/numero']
                    }
                }
            }
        }, status_code=409)  # 409 Conflict

    departement = departements[0]

    # Try to get an existing object
    driver = Driver.query.options(joinedload(Driver.departement)).filter_by(
        departement=departement,
        professional_licence=args['professional_licence'],
        added_by=current_user
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
    # It may happen users raise the unique contrainst despite filtering above
    # smells like a race condition if they submit twice and fast enough
    try:
        db.session.flush()
    except psycopg2.errors.UniqueViolation:
        db.session.rollback()
        return make_error_json_response({'data': {'0': {}}}, status_code=409)  # 409 Conflict

    ret = schema.dump({'data': [driver]})

    db.session.commit()

    return ret, status_code
