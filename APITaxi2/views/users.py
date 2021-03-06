from flask import Blueprint
from flask_security import login_required, roles_accepted

from APITaxi_models2 import User

from .. import schemas
from ..validators import (
    make_error_json_response,
)


blueprint = Blueprint('users', __name__)


@blueprint.route('/users/<int:user_id>', methods=['GET'])
@login_required
@roles_accepted('admin')
def users_details(user_id):
    query = User.query.filter_by(id=user_id)
    user = query.one_or_none()

    if not user:
        return make_error_json_response({
            'url': ['User %s not found' % user_id]
        }, status_code=404)

    schema = schemas.DataUserPublicSchema()
    return schema.dump({'data': [user]})


@blueprint.route('/users/', methods=['GET'])
@login_required
@roles_accepted('admin')
def users_list():
    # XXX: return value is not paginated for backward compatibility. I don't
    # know what is using this endpoint, so I prefer to let it as-is for now.
    users = User.query.all()
    schema = schemas.DataUserPrivateSchema()
    return schema.dump({'data': users})
