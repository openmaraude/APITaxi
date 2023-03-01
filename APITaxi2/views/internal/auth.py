from flask import Blueprint, request
from flask_security.utils import verify_password
from marshmallow import fields, Schema, validates_schema, ValidationError
from sqlalchemy.orm import joinedload

from APITaxi_models2 import User

from APITaxi2 import activity_logs, schemas
from APITaxi2.validators import (
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('internal_auth', __name__)


class AuthSchema(Schema):
    email = fields.String(required=True)

    apikey = fields.String(required=False)
    password = fields.String(required=False)
    referrer = fields.Integer(required=False)

    @validates_schema
    def check_required(self, data, **kwargs):
        if data.get('apikey') and data.get('password'):
            raise ValidationError('Specify either apikey or password, not both.')

        if not data.get('apikey') and not data.get('password'):
            raise ValidationError('Specify apikey or password.')


DataAuthSchema = schemas.data_schema_wrapper(AuthSchema())


@blueprint.route('/internal/auth', methods=['POST'])
def auth():
    """Authenticate user. Request should specify either "apikey", or "email"
    and "password".
    """
    schema = DataAuthSchema()

    params, errors = validate_schema(schema, request.json)
    if errors:
        return make_error_json_response(errors)

    args = params['data'][0]

    query = User.query.options(
        joinedload(User.manager),
        joinedload(User.managed)
    ).filter_by(
        email=args['email']
    )

    if args.get('apikey'):
        query = query.filter_by(apikey=args.get('apikey'))

    user = query.one_or_none()

    if not user or (
        args.get('password') and not verify_password(args['password'], user.password)
    ):
        return make_error_json_response({
            'data': {
                '0': {
                    '': ['Invalid credentials.']
                }
            }
        }, status_code=401)

    if args.get('apikey'):
        activity_logs.log_user_login_apikey(user.id, referrer=args.get('referrer'))
    else:
        activity_logs.log_user_login_password(user.id, referrer=args.get('referrer'))

    dump_schema = schemas.DataUserSchema()
    return dump_schema.dump({'data': [user]})
