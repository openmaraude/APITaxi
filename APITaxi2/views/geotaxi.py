import socket
import time

from flask import Blueprint, current_app, request
import redis

from APITaxi_models2 import db, Taxi, Vehicle, VehicleDescription

from .. import schemas
from ..security import auth, current_user
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


def _update_redis(pipe, data, operator):
    now = int(time.time())
    taxi_id = data['taxi_id']
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
    # GEOADD geoindex (expired after two minutes by clean_geoindex_timestamps)
    _run_redis_action(
        pipe,
        'GEOADD',
        'geoindex',
        [data['lon'], data['lat'], taxi_id],
    )
    # GEOADD geoindex_2 (expired after two minutes by clean_geoindex_timestamps)
    _run_redis_action(
        pipe,
        'GEOADD',
        'geoindex_2',
        [data['lon'], data['lat'], f"{taxi_id}:{operator}"],
    )
    #
    # We have to clean geoindex(_2) after two minutes, so we use the timestamp as a score
    # but in another sorted set.
    #
    # ZADD timestamps (expired after two minutes by clean_geoindex_timestamps)
    _run_redis_action(
        pipe,
        'ZADD',
        'timestamps',
        {f"{taxi_id}:{operator}": now},
    )
    # ZADD timestamps_id (expired after two minutes by clean_geoindex_timestamps)
    _run_redis_action(
        pipe,
        'ZADD',
        'timestamps_id',
        {taxi_id: now},
    )


@blueprint.route('/geotaxi/', methods=['POST'])
@auth.login_required(role=['admin', 'operateur'])
def geotaxi_batch():
    """
    ---
    post:
        tags:
            - operator
        summary: Update the position of many taxis at once (up to 50).
        description: |
            All data must be valid or the whole request will be rejected.

            Positions are in the WGS 84 or EPSG:3857 standard (the same as GPS).
            Beware not to invert latitude (Y) and longitude (X)!
        requestBody:
            content:
                application/json:
                    schema: DataGeotaxiSchema
                    example:
                        {
                            "data": [
                                {
                                    "positions": [
                                        {
                                            "taxi_id": "cZQHY5q",
                                            "lat": 48.85998,
                                            "lon": 2.34998
                                        },
                                        {
                                            "taxi_id": "kF9XkQ2",
                                            "lat": 49.4396,
                                            "lon": 1.0945
                                        }
                                    ]
                                }
                            ]
                        }
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
        _update_redis(pipe, position, current_user.email)
    pipe.execute()

    return '', 200
