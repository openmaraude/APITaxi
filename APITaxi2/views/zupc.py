from flask import Blueprint, request
from flask_security import login_required
from sqlalchemy import func, or_

from APITaxi_models2 import Town, ZUPC

from .. import influx_backend
from .. import schemas
from ..validators import (
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('zupc', __name__)


@blueprint.route('/zupc', methods=['GET'])
@login_required
def zupc_list():
    """
    This endpoint is only used by the console and is not part of the public API.
    ---
    get:
      description: Get data about ZUPC.
      parameters:
        - in: query
          schema: ListZUPCQueryStringSchema
      security:
        - ApiKeyAuth: []
      responses:
        200:
          description: List of ZUPC.
          content:
            application/json:
              schema: DataZUPCSchema
    """
    querystring_schema = schemas.ListZUPCQueryStringSchema()
    args, errors = validate_schema(querystring_schema, request.args)
    if errors:
        return make_error_json_response(errors)

    schema = schemas.DataZUPCSchema()

    towns = Town.query.filter(
        func.ST_Intersects(Town.shape, 'Point({} {})'.format(args['lon'], args['lat'])),
    ).all()

    if not towns:
        return schema.dump({'data': []})

    zupcs = ZUPC.query.filter(
        or_(ZUPC.allowed.contains(town) for town in towns)
    ).order_by(
        ZUPC.id
    ).all()

    if not zupcs:
        ret = schema.dump({
            'data': [(town, {
                'total': influx_backend.get_nb_active_taxis(insee_code=town.insee),
            }) for town in towns]
        })
        return ret

    ret = schema.dump({
        'data': [(zupc, {
            'total': influx_backend.get_nb_active_taxis(zupc_id=zupc.zupc_id),
        }) for zupc in zupcs]
    })
    return ret
