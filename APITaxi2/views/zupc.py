import functools
import json

from flask import Blueprint, request
from flask_security import current_user, login_required, roles_accepted
from sqlalchemy import cast, func, or_

from geoalchemy2 import Geometry

from APITaxi_models2 import db, Town, ZUPC
from APITaxi_models2.zupc import town_zupc

from .. import stats_backend
from .. import schemas
from ..validators import (
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('zupc', __name__)


def _get_zupc_stats(filter_name, filter_value, include_total, include_operators):
    """`filter_name` is either "insee_code" or "zupc_id", which are parameters
    expected by influx_backend.get_nb_active_taxis.

    If include_admin is True, this function returns the total number of taxis
    within the INSEE code or ZUPC.
    If include_operators is True, it also returns the number of taxis of
    the current user.
    """
    stats = {}
    if include_total:
        stats['total'] = stats_backend.get_nb_active_taxis(**{filter_name: filter_value})
    if include_operators:
        stats['operators'] = {
            current_user.email: stats_backend.get_nb_active_taxis(
                **{filter_name: filter_value},
                operator=current_user.email
            )
        }
    return stats


@blueprint.route('/zupc', methods=['GET'])
@login_required
def zupc_list():
    """
    Get the list of ZUPC known and used by the API.

    This endpoint is only used by the console and is not part of the public API.
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

    is_admin = current_user.has_role('admin')
    is_operator = current_user.has_role('operateur')

    if not zupcs:
        ret = schema.dump({
            'data': [
                (town, _get_zupc_stats('insee_code', town.insee, is_admin, is_operator))
                for town in towns
            ]
        })
        return ret

    ret = schema.dump({
        'data': [
            (zupc, _get_zupc_stats('zupc_id', zupc.zupc_id, is_admin, is_operator))
            for zupc in zupcs
        ]
    })
    return ret


@blueprint.route('/zupc/live', methods=['GET'])
@login_required
def zupc_live():
    """List all ZUPCs, and number of taxis connected.

    This endpoint is only used by the console and is not part of the public API.
    """
    query = db.session.query(
        ZUPC.zupc_id,
        ZUPC.nom,
        func.ST_ASGEOJSON(
            func.ST_UNION(
                cast(Town.shape, Geometry(srid=4326))
            )
        ).label('geojson')
    ).join(
        town_zupc, town_zupc.c.zupc_id == ZUPC.id
    ).join(
        Town
    ).group_by(
        ZUPC.id,
        ZUPC.nom
    )

    zupcs = query.all()
    is_admin = current_user.has_role('admin')
    is_operator = current_user.has_role('operateur')

    schema = schemas.DataZUPCGeomSchema()
    return schema.dump({
        'data': [{
            'id': zupc.zupc_id,
            'nom': zupc.nom,
            'geojson': json.loads(zupc.geojson),
            'stats': _get_zupc_stats('zupc_id', zupc.zupc_id, is_admin, is_operator),
        } for zupc in zupcs]
    })


@functools.lru_cache()  # Store in memory (~100k VIRT ~32k RES ~5k SHR for the full list)
def _dump_towns(search):
    schema = schemas.DataTownSchema()

    towns = db.session.query(Town.insee, Town.name).order_by(Town.name)
    if search:
        towns = towns.filter(Town.name.ilike(search + '%'))

    return schema.dump({'data': towns})


@blueprint.route('/towns', methods=['GET'])
@login_required
@roles_accepted('admin', 'moteur', 'operateur')
def town_list():
    """
    This endpoint is not part of the public API but can be convenient to integrate le.taxi.
    ---
    get:
      tags:
        - both
      summary: List of towns accepted by le.taxi to register taxis.
      description: |
        Should be updated at the beginning of every year.

        This does not include the geographical data. You can find them on
        https://www.data.gouv.fr/fr/datasets/decoupage-administratif-communal-francais-issu-d-openstreetmap/
      parameters:
        - in: query
          schema: ListTownQueryStringSchema
      security:
        - ApiKeyAuth: []
      responses:
        200:
          description: Return a list of pairs of (INSEE, name).
          content:
            application/json:
              schema: DataTownSchema
    """
    querystring_schema = schemas.ListTownQueryStringSchema()
    args, errors = validate_schema(querystring_schema, request.args)
    if errors:
        return make_error_json_response(errors)

    return _dump_towns(args.get('search'))
