from flask import Blueprint, request
from flask_security.utils import verify_password
from marshmallow import fields, Schema

from APITaxi_models2 import User

from APITaxi2 import schemas
from APITaxi2.validators import (
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('internal.auth', __name__)


class AuthSchema(Schema):
    email = fields.String(required=True)
    password = fields.String(required=True)


@blueprint.route('/internal/auth', methods=['POST'])
def auth():
    schema = AuthSchema()

    params, errors = validate_schema(schema, request.json)
    if errors:
        return make_error_json_response(errors)

    user = User.query.filter_by(email=params['email']).one_or_none()
    if not user or not verify_password(params['password'], user.password):
        return make_error_json_response({
            'data': {
                '0': {
                    '': ['Invalid credentials.']
                }
            }
        }, status_code=401)

    dump_schema = schemas.DataUserPrivateSchema()
    return dump_schema.dump({'data': [user]})
