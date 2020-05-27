from sqlalchemy import func
from sqlalchemy.orm import joinedload

from flask import abort, Blueprint, request
from flask_security import current_user, login_required, roles_accepted

from marshmallow import fields, Schema, validates_schema, ValidationError

from APITaxi_models2 import Departement, Driver, db

from ..validators import (
    data_schema_wrapper,
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('drivers', __name__)


def drivers_create_schema():
    class DepartementSchema(Schema):
        nom = fields.String()
        numero = fields.String()

        @validates_schema
        def check_required(self, data, **kwargs):
            if 'nom' not in data and 'numero' not in data:
                raise ValidationError(
                    'You need to specify at least "nom" or "numero"', 'nom'
                )

    class DriverSchema(Schema):
        first_name = fields.String(required=True)
        last_name = fields.String(required=True)
        birth_date = fields.Date(allow_none=True)
        professional_licence = fields.String(required=True)
        departement = fields.Nested(DepartementSchema, required=True)

    return data_schema_wrapper(DriverSchema)


@blueprint.route('/drivers', methods=['POST'])
@login_required
@roles_accepted('admin', 'operateur', 'preferecture')
def drivers_create():
    schema = drivers_create_schema()()
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
    ).one_or_none()

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
