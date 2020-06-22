from flask import Blueprint
from flask_security import current_user, login_required, roles_accepted

from sqlalchemy.orm import joinedload

from APITaxi_models2 import Hail

from .. import redis_backend, schemas
from ..validators import make_error_json_response


blueprint = Blueprint('hails', __name__)


@blueprint.route('/hails/<string:hail_id>', methods=['GET'])
@login_required
@roles_accepted('admin', 'moteur', 'operateur')
def hails_details(hail_id):
    hail = Hail.query.options(
        joinedload(Hail.taxi)
    ).options(
        joinedload(Hail.added_by)
    ).options(
        joinedload(Hail.operateur)
    ).get(hail_id)
    if not hail:
        return make_error_json_response({
            'url': 'Hail not found'
        }, status_code=404)
    if current_user not in (hail.operateur, hail.added_by) and not current_user.has_role('admin'):
        return make_error_json_response({
            'url': 'You do not have the permissions to view this hail'
        }, status_code=403)

    schema = schemas.data_schema_wrapper(schemas.HailSchema)()
    taxi_position = redis_backend.get_taxi(hail.taxi_id, hail.added_by.email)
    return schema.dump({'data': [(hail, taxi_position)]})


