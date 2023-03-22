from flask import Blueprint, request
from flask_security import current_user, login_required
from flask_security.utils import hash_password

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload, aliased

from APITaxi_models2 import db, Role, User

from .. import schemas
from ..validators import (
    make_error_json_response,
    validate_schema,
)


blueprint = Blueprint('users', __name__)


@blueprint.route('/users/<int:user_id>', methods=['GET', 'PUT'])
@login_required
def users_details(user_id):
    query = User.query.options(
        joinedload(User.manager),
        joinedload(User.managed)
    ).filter_by(id=user_id)

    user = query.one_or_none()
    if not user:
        return make_error_json_response({
            'url': ['User %s not found.' % user_id]
        }, status_code=404)

    if current_user != user and not current_user.has_role('admin'):
        return make_error_json_response({
            'url': ['You do not have the permissions to access this user.']
        }, status_code=403)

    schema = schemas.DataUserSchema()

    if request.method == 'GET':
        return schema.dump({'data': [user]})

    params, errors = validate_schema(schema, request.json, partial=True)
    if errors:
        return make_error_json_response(errors)

    args = request.json.get('data', [{}])[0]

    # It is not yet possible to update the fields "roles" and "manager".
    # Email should **not** be editable, as it is used as a fixed identifier for
    # the account.
    # It is not possible yet to update api key.
    for field in (
        (User.commercial_name, 'name'),
        (User.email_customer, 'email_customer'),
        (User.email_technical, 'email_technical'),
        (User.hail_endpoint_production, 'hail_endpoint_production'),
        (User.phone_number_customer, 'phone_number_customer'),
        (User.phone_number_technical, 'phone_number_technical'),
        (User.operator_api_key, 'operator_api_key'),
        (User.operator_header_name, 'operator_header_name'),
    ):
        model_name, arg_name = field
        if arg_name in args:
            value = args[arg_name]
            # All of these fields are strings
            if value is None:
                value = ''
            setattr(user, model_name.name, value)

    if args.get('password'):
        user.password = hash_password(args['password'])

    ret = schema.dump({'data': [user]})
    db.session.commit()
    return ret


@blueprint.route('/users/', methods=['GET'])
@login_required
def users_list():
    """If user is administrator, list all accounts. Otherwise, list all managed
    accounts.
    """
    querystring_schema = schemas.ListUserQuerystringSchema()
    querystring, errors = validate_schema(querystring_schema, dict(request.args.lists()))
    if errors:
        return make_error_json_response(errors)

    query = User.query.options(
        joinedload(User.manager),
        joinedload(User.managed)
    ).order_by(User.id)

    # Administrators can list all users. Regular users only the accounts they manage.
    if current_user.has_role('admin'):
        if 'manager' in querystring:
            Manager = aliased(User)
            query = query.outerjoin(Manager, User.manager_id == Manager.id).filter(or_(*[
                func.lower(Manager.email).contains(value.lower())
                for value in querystring['manager']
            ]))
        if 'role' in querystring:
            query = query.join(User.roles).filter(or_(*[
                Role.name == value for value in querystring['role']
            ]))
    else:
        query = query.filter_by(manager=current_user)

    if 'email' in querystring:
        query = query.filter(or_(*[
            func.lower(User.email).contains(value.lower())
            for value in querystring['email']
        ]))
    if 'name' in querystring:
        query = query.filter(or_(*[
            func.lower(User.commercial_name).contains(value.lower())
            for value in querystring['name']
        ]))

    users = query.paginate(
        page=querystring.get('p', [1])[0],
        per_page=30,
        error_out=False  # if True, invalid page or pages without results raise 404
    )

    schema = schemas.DataUserListSchema()
    return schema.dump({
        'data': users.items,
        'meta': users,
    })
