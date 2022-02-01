import socket
import time

from flask import Blueprint, current_app, request
from flask_security import current_user, login_required, roles_accepted
import redis

from APITaxi_models2 import db, Taxi, Vehicle, VehicleDescription

from .. import schemas
from ..validators import (
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('geotaxi', __name__)


def _run_redis_action(pipe, action, *params):
    action = getattr(pipe, action.lower())

    # Run action
    try:
        action(*params)
    except socket.error:
        current_app.logger.error(
            'Error while running redis action %s %s',
            action.__name__.upper(),
            ' '.join([str(param) for param in params])
        )
    except redis.RedisError as e:
        current_app.logger.error(
            'Error while running redis action %s %s %s',
            action.__name__.upper(),
            ' '.join([str(param) for param in params]),
            e
        )


def _update_redis(pipe, data, user):
    now = int(time.time())
    taxi_id = data['taxi_id']
    operator = user.email
    # Hardcoded for backwards compatibility with the geotaxi worker
    timestamp = now
    # These fields are unused, fill them with whatever is expected
    status = 'free'  # light status, the actual status is read from VehicleDescription
    device = 'phone'
    version = 2

    # HSET taxi:<id>
    _run_redis_action(
        pipe,
        'HSET',
        f"taxi:{taxi_id}",
        operator,
        f"{timestamp} {data['lat']} {data['lon']} {status} {device} {version}",
    )
    # GEOADD geoindex
    _run_redis_action(
        pipe,
        'GEOADD',
        'geoindex',
        [data['lon'], data['lat'], taxi_id],
    )
    # GEOADD geoindex_2
    _run_redis_action(
        pipe,
        'GEOADD',
        'geoindex_2',
        [data['lon'], data['lat'], f"{taxi_id}:{operator}"],
    )
    # ZADD timestamps
    _run_redis_action(
        pipe,
        'ZADD',
        'timestamps',
        {f"{taxi_id}:{operator}": now},
    )
    # ZADD timestamps_id
    _run_redis_action(
        pipe,
        'ZADD',
        'timestamps_id',
        {taxi_id: now},
    )


@blueprint.route('/geotaxi/', methods=['POST'])
@login_required
@roles_accepted('admin', 'operateur')
def geotaxi_batch():
    """
    ---
    post:
        summary: Update the position of many taxis at once (up to 50).
        description: |
            All data must be valid or the whole request will be rejected.

            Positions are in the WGS 84 or EPSG:3857 standard (the same as GPS).
        requestBody:
            content:
                application/json:
                    schema: DataGeotaxiSchema
        security:
            - ApiKeyAuth: []
        responses:
            200:
                description: All the taxi positions were updated
    """
    schema = schemas.DataGeotaxiSchema()
    params, errors = validate_schema(schema, request.json)
    if errors:
        return make_error_json_response(errors)

    data = params['data'][0]
    positions = data['positions']
    requested_taxi_ids = dict((position['taxi_id'], position) for position in positions)

    valid_taxi_ids = {id_ for id_, in db.session.query(Taxi.id).join(Vehicle).join(VehicleDescription).filter(
        Taxi.id.in_(requested_taxi_ids),
        # For taxis registered with several operators, filter on the description,
        # not the Taxi.added_by
        VehicleDescription.added_by == current_user
    ).all()}

    # Check all taxis are declared to us and belong to this operator
    unknown_taxi_ids = set(requested_taxi_ids) - valid_taxi_ids
    if unknown_taxi_ids:
        validation_errors = {}
        for i, position in enumerate(positions):
            if position['taxi_id'] in unknown_taxi_ids:
                validation_errors[i] = {'taxi_id': ["Identifiant de taxi inconnu"]}
        # Reject the whole request if a taxi ID is invalid
        return make_error_json_response({'data': {0: {'positions': validation_errors}}})

    # Record the new position
    # (we rejected the query on the slightest error, so the dict only contains valid data)
    pipe = current_app.redis.pipeline()
    for position in requested_taxi_ids.values():
        _update_redis(pipe, position, current_user)
    pipe.execute()

    return '', 200
