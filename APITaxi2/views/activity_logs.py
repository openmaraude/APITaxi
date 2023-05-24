from flask import Blueprint, request, current_app
from marshmallow import fields, Schema, validate, ValidationError
from sqlalchemy import select, desc

from APITaxi2 import activity_logs, schemas, validators
from APITaxi_models2 import db
from APITaxi_models2.activity_logs import activity_log

from ..security import auth, current_user


blueprint = Blueprint('activity_logs', __name__)


class ActivityLogsSchema(Schema, schemas.PageQueryStringMixin):
    id = fields.String(dump_only=True)
    time = fields.DateTime()
    resource = fields.String(
        validate=validate.OneOf(activity_logs.RESOURCES),
        allow_none=True,
        required=False,
    )
    resource_id = fields.String()
    action = fields.String(
        validate=validate.OneOf(activity_logs.ACTIONS),
        allow_none=True,
        required=False,
    )
    extra = fields.Dict(required=False, dump_only=True)


DataActivityLogsSchema = schemas.data_schema_wrapper(ActivityLogsSchema())


@blueprint.route('/activity_logs', methods=['GET'])
@auth.login_required(role=['admin'])
def activity_logs_list():
    """"""
    querystring_schema = ActivityLogsSchema()
    querystring, errors = validators.validate_schema(querystring_schema, request.args)
    if errors:
        return validators.make_error_json_response(errors)

    query = select(activity_log).order_by(desc('time'))
    if querystring.get('resource'):
        query = query.filter_by(resource=querystring['resource'])
    if querystring.get('resource_id'):
        query = query.filter_by(resource_id=querystring['resource_id'])
    if querystring.get('action'):
        query = query.filter_by(action=querystring['action'])

    # TODO paginate but requires SQLAlchemy 2.x
    query = query.limit(100)

    with db.engine.connect() as conn:
        result = conn.execute(query)

    data = ({
        # MUI wants an Id column
        'id': "-".join([str(row['time']), row['resource'], row['resource_id']]),
        **row
    } for row in result)

    dump_schema = DataActivityLogsSchema()
    return dump_schema.dump({'data': data})
