from flask import Blueprint, request, current_app
from marshmallow import fields, Schema, validate, ValidationError

from APITaxi2 import activity_logs, schemas, validators
from APITaxi_models2 import db
from APITaxi_models2.activity_logs import ActivityLog

from ..security import auth, current_user


blueprint = Blueprint('activity_logs', __name__)


class ActivityLogsQueryStringSchema(Schema, schemas.PageQueryStringMixin):
    resource = fields.List(fields.String(
        validate=validate.OneOf(activity_logs.RESOURCES),
        allow_none=True,
        required=False,
    ))
    resource_id = fields.List(fields.String())
    action = fields.List(fields.String(
        validate=validate.OneOf(activity_logs.ACTIONS),
        allow_none=True,
        required=False,
    ))


class ActivityLogsSchema(Schema):
    id = fields.String()
    time = fields.DateTime()
    resource = fields.String()
    resource_id = fields.String()
    action = fields.String()
    extra = fields.Dict()


DataActivityLogsSchema = schemas.data_schema_wrapper(ActivityLogsSchema(), with_pagination=True)


@blueprint.route('/activity_logs', methods=['GET'])
@auth.login_required(role=['admin'])
def activity_logs_list():
    """"""
    querystring_schema = ActivityLogsQueryStringSchema()
    querystring, errors = validators.validate_schema(querystring_schema, dict(request.args.lists()))
    if errors:
        return validators.make_error_json_response(errors)

    query = ActivityLog.query.order_by(ActivityLog.id.desc(), ActivityLog.time.desc())
    if querystring.get('resource'):
        query = query.filter_by(resource=querystring['resource'][0])
    if querystring.get('resource_id'):
        query = query.filter_by(resource_id=querystring['resource_id'][0])
    if querystring.get('action'):
        query = query.filter_by(action=querystring['action'][0])

    page = query.paginate(
        page=querystring.get('p', [1])[0],
        per_page=30,
        error_out=False  # if True, invalid page or pages without results raise 404
    )

    dump_schema = DataActivityLogsSchema()
    return dump_schema.dump({
        'data': page.items,
        'meta': page
    })
