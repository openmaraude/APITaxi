from flask import Blueprint, request
from flask_security import current_user, login_required, roles_accepted

from APITaxi_models2 import Customer, db

from .. import schemas
from ..validators import (
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('customers', __name__)


@blueprint.route('/customers/<string:customer_id>', methods=['PUT'])
@login_required
@roles_accepted('admin', 'moteur')
def customers_edit(customer_id):
    """
    ---
    put:
      description: Update customer data.
      parameters:
        - name: customer_id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema: DataCustomerSchema
      security:
        - ApiKeyAuth: []
      responses:
        200:
          description: Return the updated resource.
          content:
            application/json:
              schema: DataCustomerSchema
    """
    schema = schemas.data_schema_wrapper(schemas.CustomerSchema(current_user))()
    params, errors = validate_schema(schema, request.json)
    if errors:
        return make_error_json_response(errors)

    args = params['data'][0]

    query = Customer.query.filter_by(id=customer_id, added_by=current_user)
    customer = query.one_or_none()
    if not customer:
        return make_error_json_response({
            'url': ['No customer %s found associated to user %s' % (customer_id, current_user.email)]
        }, status_code=404)

    for attr in ['reprieve_begin', 'reprieve_end', 'ban_begin', 'ban_end']:
        if attr not in args:
            continue
        setattr(customer, attr, args[attr])

    db.session.flush()

    ret = schema.dump({'data': [customer]})

    db.session.commit()

    return ret
