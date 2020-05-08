from flask import Blueprint, request
from flask_security import current_user, login_required, roles_accepted

from marshmallow import fields, Schema, validates_schema, ValidationError

from APITaxi_models2 import Customer, db

from ..validators import (
    data_schema_wrapper,
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('customers', __name__)


def customers_edit_schema(current_user):
    class CustomerSchema(Schema):
        moteur_id = fields.Int()
        reprieve_begin = fields.DateTime(allow_none=True)
        reprieve_end = fields.DateTime(allow_none=True)
        ban_begin = fields.DateTime(allow_none=True)
        ban_end = fields.DateTime(allow_none=True)

        @validates_schema
        def validate_moteur_id(self, data, **kwargs):
            """There are three cases to handle:

            1/ user is admin but not a moteur: moteur_id is required
            2/ user is admin and moteur: moteur_id is optional, and defaults to
               user's id
            3/ user is not admin: if provided, moteur_id must be equal to
               user's id
            """
            # Case 1:
            if (current_user.has_role('admin')
                and not current_user.has_role('moteur')
                and 'moteur_id' not in data
            ):
                raise ValidationError(
                    'Missing data for required field.',
                    'moteur_id'
                )

            # Case 2: nothing to do

            # Case 3:
            if (not current_user.has_role('admin')
                and 'moteur_id' in data
                and data['moteur_id'] != current_user.id
            ):
                raise ValidationError(
                    'Invalid moteur_id. Should match your user id.',
                    'moteur_id'
                )

    return data_schema_wrapper(CustomerSchema)


@blueprint.route('/customers/<string:customer_id>', methods=['PUT'])
@login_required
@roles_accepted('admin', 'moteur')
def customers_edit(customer_id):
    schema = customers_edit_schema(current_user)()
    params, errors = validate_schema(schema, request.json)
    if errors:
        return make_error_json_response(errors)

    args = params['data'][0]
    moteur_id = args.get('moteur_id', current_user.id)

    query = Customer.query.filter_by(id=customer_id, moteur_id=moteur_id)
    customer = query.one_or_none()
    if not customer:
        return make_error_json_response({
            'url': ['No customer found associated to moteur id %s' % moteur_id]
        }, status_code=404)

    for attr in ['reprieve_begin', 'reprieve_end', 'ban_begin', 'ban_end']:
        if attr not in args:
            continue
        setattr(customer, attr, args[attr])

    db.session.commit()

    return schema.dump({'data': [customer]})
