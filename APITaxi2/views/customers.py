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
    schema = schemas.data_schema_wrapper(schemas.CustomerSchema(current_user))()
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

    db.session.flush()

    ret = schema.dump({'data': [customer]})

    db.session.commit()

    return ret
