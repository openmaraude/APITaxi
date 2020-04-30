from flask import Blueprint
from flask_security import current_user, login_required, roles_accepted


blueprint = Blueprint('customers', __name__)


@blueprint.route('/customers/<string:customer_id>', methods=['PUT'])
@login_required
@roles_accepted('admin')
def customers_put(customer_id):
    return ''
