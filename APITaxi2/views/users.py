from flask import Blueprint, request
from flask_security import login_required, roles_accepted
from sqlalchemy.orm import joinedload

from APITaxi_models2 import User

from .. import schemas
from ..validators import (
    make_error_json_response,
    validate_schema,
)


blueprint = Blueprint('users', __name__)


@blueprint.route('/users/<int:user_id>', methods=['GET'])
@login_required
@roles_accepted('admin')
def users_details(user_id):
    query = User.query.options(joinedload(User.manager)).filter_by(id=user_id)
    user = query.one_or_none()

    if not user:
        return make_error_json_response({
            'url': ['User %s not found' % user_id]
        }, status_code=404)

    schema = schemas.DataUserSchema()
    return schema.dump({'data': [user]})


@blueprint.route('/users/', methods=['GET'])
@login_required
@roles_accepted('admin')
def users_list():
    querystring_schema = schemas.ListUserQuerystringSchema()
    querystring, errors = validate_schema(querystring_schema, dict(request.args.lists()))
    if errors:
        return make_error_json_response(errors)

    users = User.query.options(joinedload(User.manager)).order_by(User.id).paginate(
        page=querystring.get('p', [1])[0],
        per_page=30,
        error_out=False  # if True, invalid page or pages without results raise 404
    )

    schema = schemas.DataUserListSchema()
    return schema.dump({
        'data': users.items,
        'meta': users,
    })
