from flask import Blueprint
from flask_security import login_required, roles_accepted

from marshmallow import fields, Schema

from APITaxi_models2 import User, db

from ..validators import (
    data_schema_wrapper,
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('users', __name__)


def users_details_schema():
    class UserSchema(Schema):
        commercial_name = fields.String(data_key='name')

    return data_schema_wrapper(UserSchema)


@blueprint.route('/users/<int:user_id>', methods=['GET'])
@login_required
@roles_accepted('admin')
def users_details(user_id):
    query = User.query.filter_by(id=user_id)
    user = query.one_or_none()

    if not user:
        return make_error_json_response({
            'url': 'User %s not found' % user_id
        }, status_code=404)

    schema = users_details_schema()
    return schema().dump({'data': [user]})


def users_list_schema():
    class UserSchema(Schema):
        email = fields.String()
        apikey = fields.String()

    return data_schema_wrapper(UserSchema)


@blueprint.route('/users/', methods=['GET'])
@login_required
@roles_accepted('admin')
def users_list():
    # XXX: return value is not paginated for backward compatibility and I
    # because don't know where this endpoint is called.
    users = User.query.all()
    schema = users_list_schema()
    return schema().dump({'data': users})
