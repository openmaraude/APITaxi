from flask import Blueprint, request
from flask_security import login_required

from APITaxi_models2 import ZUPC

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

    zupcs = ZUPC.query.filter(
        ZUPC.shape.ST_Intersects('POINT(%s %s)' % (args['lon'], args['lat']))
    ).filter(
        ZUPC.id == ZUPC.parent_id
    ).order_by(
        ZUPC.id
    ).all()

    schema = schemas.DataZUPCSchema()
    ret = schema.dump({
        'data': [
            (zupc, influx_backend.get_nb_active_taxis(zupc.insee))
            for zupc in zupcs
        ]
    })
    return ret
