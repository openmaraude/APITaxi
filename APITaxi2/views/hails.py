from datetime import timedelta
import json
import time
import uuid

import geohash2

from flask import Blueprint, request
from flask_security import current_user, login_required, roles_accepted

import sqlalchemy
from sqlalchemy import func, or_
from sqlalchemy.orm import aliased, joinedload

from APITaxi_models2 import Customer, db, Hail, Taxi, User, Vehicle, VehicleDescription
from APITaxi_models2.hail import HAIL_TERMINAL_STATUS

from .. import influx_backend, redis_backend, schemas, tasks
from ..validators import (
    make_error_json_response,
    validate_schema
)


# Sentinel, used to make the difference between a None value and a value not set. Given a dictionary:
#
# >>> d = {'yes': None}
#
# Then:
#
# >>> d.get('yes', NOT_PROVIDED)
# None
# >>> d.get('no', NOT_PROVIDED)
# NOT_PROVIDED
#
NOT_PROVIDED = object()


blueprint = Blueprint('hails', __name__)


def _get_short_uuid():
    return str(uuid.uuid4())[0:7]


def _set_hail_status(hail, vehicle_description, new_status, new_taxi_phone_number):
    """Change `hail`'s status to `new_status`. Raises ValueError if the change
    is impossible.

    Some status also change `vehicle_description`.status. For example, if the
    new hail status is "accepted_by_customer", vehicle_description.status becomes
    "oncoming".

    `new_status` is expected to be a valid value.

    Returns True if the status has changed, False otherwise.
    """
    if new_status is NOT_PROVIDED or hail.status == new_status:
        return False

    if hail.status in HAIL_TERMINAL_STATUS:
        raise ValueError(f'Hail status is {hail.status} and cannot be changed to {new_status}')

    # There are two ways to provide the taxi phone number:
    # - when we call the operator's API to request the taxi, it can be returned
    # - or it needs to be provided when the taxi accepts the trip.
    if new_status == 'accepted_by_taxi':
        if new_taxi_phone_number:
            hail.taxi_phone_number = new_taxi_phone_number
        elif not hail.taxi_phone_number:
            raise ValueError('Status changes to accepted_by_taxi but taxi_phone_number is not provided')

    # TRANSITIONS define the permissions required to go from a state to another.
    # Top level keys are the origin hails' status. Subkeys are the possible future state, and values the permission
    # required to perform the transition.
    TRANSITIONS = {
        'received': {
            'declined_by_customer': 'moteur',
        },
        'sent_to_operator': {
            'declined_by_customer': 'moteur',
        },
        'received_by_operator': {
            'declined_by_customer': 'moteur',
            'received_by_taxi': 'operateur',
        },
        'received_by_taxi': {
            'accepted_by_taxi': 'operateur',
            'declined_by_taxi': 'operateur',
            'incident_taxi': 'operateur',
            'incident_customer': 'moteur',
            'declined_by_customer': 'moteur',
        },
        'accepted_by_taxi': {
            'incident_customer': 'moteur',
            'declined_by_customer': 'moteur',
            'accepted_by_customer': 'moteur',
            'incident_taxi': 'operateur',
        },
        'accepted_by_customer': {
            'customer_on_board': 'operateur',
            'incident_customer': 'moteur',
            'incident_taxi': 'operateur',
        },
        'customer_on_board': {
            'incident_customer': 'moteur',
            'incident_taxi': 'operateur',
            'finished': 'operateur',
        }
    }
    if hail.status in TRANSITIONS:
        if new_status not in TRANSITIONS[hail.status]:
            raise ValueError(f'Impossible to set status from {hail.status} to {new_status}')
        if (
            not current_user.has_role(TRANSITIONS[hail.status][new_status])
            and not current_user.has_role('admin')
        ):
            raise ValueError(
                f'Permission {TRANSITIONS[hail.status][new_status]} is required to change status '
                f'from {hail.status} to {new_status}'
            )

    hail.status = new_status

    # Keys are the new hail's status, values the new taxi's status.
    new_taxi_status = {
        'accepted_by_customer': 'oncoming',
        'declined_by_customer': 'free',
        'declined_by_taxi': 'off',
        'customer_on_board': 'occupied',
        'incident_taxi': 'free',
        'incident_customer': 'free',
        'finished': 'free',
    }

    if new_status in new_taxi_status:
        vehicle_description.status = new_taxi_status[new_status]

    return True


def _set_hail_values(hail, fields, args, enough_perms):
    """Helper function to update hail.

    Params:
    - hail: hail to update.
    - fields: list of fields to check for update. Each field may be present or
              not in "args".
    - args: the POST data.
    - enough_perms: if a new value is provided and enough_perms is False,
                    return an error.

    Returns a tuple, first element is a dictionary of values changed, second an
    error response.
    """
    updates = {}
    for field in fields:
        value = args.get(field, NOT_PROVIDED)
        # If value is not provided or similar than before, do nothing
        if value is NOT_PROVIDED or value == getattr(hail, field):
            continue

        if not enough_perms:
            return None, make_error_json_response({
                'data': {
                    '0': {
                        field: ['You do not have the permissions to change this value']
                    }
                }
            })
        # Save old value
        old_value = getattr(hail, field)
        # Set new value
        setattr(hail, field, value)
        # Store change in `updates`
        updates[field] = (old_value, value)
    return updates, None


def _unban_customer(customer):
    customer.ban_begin = None
    customer.ban_end = None


def _ban_is_ongoing(customer):
    """Returns True if customer has an ongoing ban."""
    if not customer.ban_end:
        return False

    res = db.session.query(customer.ban_end >= sqlalchemy.func.NOW()).scalar()
    return res


def _ban_customer(customer):
    """Ban customer. Several cases:

    1. Customer is already flagged as banned:
        a) ban is finished: ban customer for 24 hours
        b) ban is still ongoing: double the ban time

    2. Customer is not flagged as banned: ban for 24 hours
    """
    # Case 1.
    if customer.ban_begin and customer.ban_end:
        # 1. a)
        if not _ban_is_ongoing(customer):
            customer.ban_begin = sqlalchemy.func.NOW()
            customer.ban_end = sqlalchemy.func.NOW() + timedelta(hours=+24)
        # 1. b)
        else:
            ban_duration = customer.ban_end - customer.ban_begin
            customer.ban_end = customer.ban_end + ban_duration
    # Case 2
    else:
        customer.ban_begin = sqlalchemy.func.NOW()
        customer.ban_end = sqlalchemy.func.NOW() + timedelta(hours=+24)


@blueprint.route('/hails/<string:hail_id>', methods=['GET', 'PUT'])
@login_required
@roles_accepted('admin', 'moteur', 'operateur')
def hails_details(hail_id):
    """
    ---
    get:
      description: Get hail details.
      parameters:
        - name: hail_id
          in: path
          required: true
          schema:
            type: string
      security:
        - ApiKeyAuth: []
      responses:
        200:
          description: Get hail details.
          content:
            application/json:
              schema: DataHailSchema

    put:
      description: Edit hail details.
      parameters:
        - name: hail_id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema: DataHailSchema
      security:
        - ApiKeyAuth: []
      responses:
        200:
          description: Update hail details.
          content:
            application/json:
              schema: DataHailSchema
    """
    query = db.session.query(
        Hail, VehicleDescription
    ).options(
        joinedload(Hail.taxi),
        joinedload(Hail.added_by),
        joinedload(Hail.operateur),
        joinedload(Hail.customer)
    ).join(
        Taxi, Taxi.id == Hail.taxi_id
    ).join(
        Vehicle
    ).filter(
        Hail.taxi_id == Taxi.id,
        Taxi.vehicle_id == Vehicle.id,
        VehicleDescription.vehicle_id == Vehicle.id,
        VehicleDescription.added_by_id == Hail.operateur_id,
        Hail.id == hail_id
    ).one_or_none()
    if not query:
        return make_error_json_response({
            'url': ['Hail not found']
        }, status_code=404)

    hail, vehicle_description = query

    if current_user not in (hail.operateur, hail.added_by) and not current_user.has_role('admin'):
        return make_error_json_response({
            'url': ['You do not have the permissions to view this hail']
        }, status_code=403)

    schema = schemas.DataHailSchema()
    taxi_position = redis_backend.get_taxi(hail.taxi_id, hail.operateur.email)

    if request.method == 'GET':
        return schema.dump({'data': [(hail, taxi_position)]})

    params, errors = validate_schema(schema, request.json, partial=True)
    if errors:
        return make_error_json_response(errors)

    args = request.json['data'][0]

    hail_initial_status = hail.status

    try:
        status_changed = _set_hail_status(
            hail,
            vehicle_description,
            args.get('status', NOT_PROVIDED),
            args.get('taxi_phone_number')
        )
    except ValueError as exc:
        return make_error_json_response({
            'data': {
                '0': {
                    'status': [str(exc)]
                }
            }
        })

    # Update hail with values provided as params. If the new value is different
    # from the existing one, require the user to be the operateur of the hail.
    operateur_changes, error = _set_hail_values(
        hail,
        [
            'incident_taxi_reason',
            'reporting_customer',
            'reporting_customer_reason'
        ],
        args,
        hail.operateur == current_user or current_user.has_role('admin')
    )
    if error:
        return error

    # Same for customer fields.
    moteur_changes, error = _set_hail_values(
        hail,
        [
            'customer_lon',
            'customer_lat',
            'customer_address',
            'customer_phone_number',
            'rating_ride',
            'rating_ride_reason',
            'incident_customer_reason'
        ],
        args,
        hail.added_by == current_user or current_user.has_role('admin')
    )
    if error:
        return error

    # If reporting_customer is provided and different from the previous value,
    # ban or unban the customer depending on the new value.
    if 'reporting_customer' in operateur_changes:
        if not hail.reporting_customer:
            _unban_customer(hail.customer)
        else:
            _ban_customer(hail.customer)

    ret = schema.dump({'data': [(hail, taxi_position)]})
    db.session.commit()

    # If the PUT request changed any field of the object, log the request. Do
    # nothing if the object didn't change.
    if status_changed or operateur_changes or moteur_changes:
        redis_backend.log_hail(
            hail_id=hail.id,
            http_method='PUT',
            request_payload=json.dumps(request.json, indent=2),
            hail_initial_status=hail_initial_status,
            hail_final_status=hail.status,
            request_user=current_user,
            response_payload=json.dumps(ret, indent=2),
            response_status_code=200
        )

    if status_changed:
        # Hail has been received by taxi. Taxi has 30 seconds to accept or
        # refuse the hail until timeout.
        if hail.status == 'received_by_taxi':
            tasks.operators.handle_hail_timeout.apply_async(
                args=(hail.id, vehicle_description.added_by_id),
                kwargs={
                    'initial_hail_status': 'received_by_taxi',
                    'new_hail_status': 'timeout_taxi',
                    'new_taxi_status': 'off'
                },
                countdown=30
            )
        # Hail has been accepted by the taxi. Customer has 1 minute to accept
        # or refuse the hail. If not, hail becomes "timeout_customer" and taxi
        # is free again.
        elif hail.status == 'accepted_by_taxi':
            tasks.operators.handle_hail_timeout.apply_async(
                args=(hail.id, vehicle_description.added_by_id),
                kwargs={
                    'initial_hail_status': 'accepted_by_taxi',
                    'new_hail_status': 'timeout_customer',
                    'new_taxi_status': 'free'
                },
                countdown=60
            )
        # Hail is accepted by customer. Taxi has 30 minutes to pickup the
        # customer and change status to customer_on_board.
        elif hail.status == 'accepted_by_customer':
            tasks.operators.handle_hail_timeout.apply_async(
                args=(hail.id, vehicle_description.added_by_id),
                kwargs={
                    'initial_hail_status': 'accepted_by_customer',
                    'new_hail_status': 'timeout_accepted_by_customer',
                    'new_taxi_status': 'occupied'
                },
                countdown=60 * 30
            )
        # Call timeout if customer is still on board after 2 hours.
        elif hail.status == 'customer_on_board':
            tasks.operators.handle_hail_timeout.apply_async(
                args=(hail.id, vehicle_description.added_by_id),
                kwargs={
                    'initial_hail_status': 'customer_on_board',
                    'new_hail_status': 'timeout_taxi',
                    'new_taxi_status': 'off'
                },
                countdown=60 * 60 * 2
            )
    return ret


@blueprint.route('/hails/', methods=['GET'])
@login_required
@roles_accepted('admin', 'moteur', 'operateur')
def hails_list():
    """Returns the list of hails paginated.

    Accept querystring arguments ?p, ?status, ?date, ?operateur, ?operateur and
    ?taxi_id.

    Pagination is returned in the "meta" field.
    ---
    get:
      description: List hails.
      parameters:
        - in: query
          schema: ListHailQuerystringSchema
      security:
        - ApiKeyAuth: []
      responses:
        200:
          description: List of hails.
          content:
            application/json:
              schema: DataHailListSchema
    """
    querystring_schema = schemas.ListHailQuerystringSchema()
    querystring, errors = validate_schema(querystring_schema, dict(request.args.lists()))
    if errors:
        return make_error_json_response(errors)

    moteur_table = aliased(User)
    operateur_table = aliased(User)
    query = Hail.query.options(
        joinedload(Hail.added_by),
        joinedload(Hail.operateur)
    ).join(
        moteur_table, moteur_table.id == Hail.added_by_id
    ).join(
        operateur_table, operateur_table.id == Hail.operateur_id
    )

    # If current user is not administrator, only allow user to get hails he is
    # the operator or the moteur of.
    if not current_user.has_role('admin'):
        filters = []
        if current_user.has_role('moteur'):
            filters.append(Hail.added_by == current_user)
        if current_user.has_role('operateur'):
            filters.append(Hail.operateur == current_user)
        query = query.filter(or_(*filters))

    # Filter on querystring arguments
    for qname, field in (
        ('status', Hail.status),
        ('date', func.date(Hail.creation_datetime)),
        ('operateur', operateur_table.email),
        ('moteur', moteur_table.email),
        ('taxi_id', Hail.taxi_id),
    ):
        if qname not in querystring:
            continue
        query = query.filter(or_(*[
            field == value for value in querystring[qname]
        ]))

    # Order by date
    query = query.order_by(Hail.creation_datetime.desc())

    # Paginate
    hails = query.paginate(
        page=querystring.get('p', [1])[0],
        per_page=30,
        error_out=False  # if True, invalid page or pages without results raise 404
    )

    schema = schemas.DataHailListSchema()
    ret = schema.dump({
        'data': hails.items,
        'meta': hails
    })

    return ret


@blueprint.route('/hails/', methods=['POST'])
@login_required
@roles_accepted('admin', 'moteur')
def hails_create():
    """
    ---
    post:
      description: |
        Create a hail request.
      requestBody:
        content:
          application/json:
            schema: DataHailSchema
      security:
        - ApiKeyAuth: []
      responses:
        201:
          description: Return a new ressource.
          content:
            application/json:
              schema: DataHailSchema
    """
    schema = schemas.DataHailSchema()
    params, errors = validate_schema(schema, request.json)
    if errors:
        return make_error_json_response(errors)

    args = params['data'][0]

    # Get taxi registered with the operateur, or return HTTP/404
    res = db.session.query(
        Taxi,
        VehicleDescription
    ).options(
        joinedload(Taxi.ads),
        joinedload(VehicleDescription.added_by)
    ).join(
        User,
        VehicleDescription.added_by_id == User.id
    ).filter(
        VehicleDescription.vehicle_id == Taxi.vehicle_id,
        Taxi.id == args['taxi_id'],
        User.email == args['operateur']['email']
    ).one_or_none()
    if not res:
        return make_error_json_response({
            'data': {
                '0': {
                    'operateur': ['Unable to find taxi for this operateur.']
                }
            }
        }, status_code=404)

    taxi, vehicle_description = res

    # Get or create Customer object
    customer = Customer.query.filter_by(moteur=current_user, id=args['customer_id']).one_or_none()
    if not customer:
        customer = Customer(
            id=args['customer_id'],
            phone_number=args['customer_phone_number'],
            moteur=current_user,

            added_by=current_user,
            added_via='api',
            added_at=func.NOW(),
            source='added_by'
        )
        db.session.add(customer)
        db.session.flush()
    elif _ban_is_ongoing(customer):
        return make_error_json_response({
            'data': {
                '0': {
                    'customer_id': ['This customer is banned.']
                }
            }
        }, status_code=403)

    # Return error if we don't have location data for the taxi.
    taxi_position = redis_backend.get_taxi(taxi.id, vehicle_description.added_by.email)
    if not taxi_position:
        return make_error_json_response({
            'data': {
                '0': {
                    'taxi_id': ['Taxi is not online.']
                }
            }
        }, status_code=400)

    # Return error if location data is too old, more than 120 seconds.
    if time.time() - taxi_position.timestamp > 120:
        return make_error_json_response({
            'data': {
                '0': {
                    'taxi_id': ['Taxi is no longer online.']
                }
            }
        }, status_code=400)

    # VehicleDescription.status must be set to free.
    if vehicle_description.status != 'free':
        return make_error_json_response({
            'data': {
                '0': {
                    'taxi_id': ['Taxi is not free.']
                }
            }
        }, status_code=400)

    hail = Hail(
        id=_get_short_uuid(),
        creation_datetime=func.NOW(),
        taxi=taxi,
        status='received',
        last_status_change=func.NOW(),
        customer=customer,
        customer_lat=args['customer_lat'],
        customer_lon=args['customer_lon'],
        operateur=vehicle_description.added_by,
        customer_address=args['customer_address'],
        customer_phone_number=args['customer_phone_number'],
        initial_taxi_lon=taxi_position.lon,
        initial_taxi_lat=taxi_position.lat,
        session_id=args.get('session_id', ''),

        added_by=current_user,
        added_via='api',
        added_at=func.NOW(),
        source='added_by'
    )
    db.session.add(hail)
    db.session.flush()

    taxi.current_hail = hail
    vehicle_description.status = 'answering'

    ret = schema.dump({'data': [(hail, taxi_position)]})

    # Since models' relationships have lazy='raise', they cannot be accessed
    # after session.commit(). Save values for later use.
    hail_operateur_email = hail.operateur.email
    taxi_ads_insee = taxi.ads.insee

    hail_endpoint_production = hail.operateur.hail_endpoint_production
    operator_header_name = hail.operateur.operator_header_name
    operator_api_key = hail.operateur.operator_api_key

    db.session.commit()

    tasks.send_request_operator.apply_async(args=[
        hail.id,
        hail_endpoint_production,
        operator_header_name,
        operator_api_key
    ])

    redis_backend.log_hail(
        hail_id=hail.id,
        http_method='POST',
        request_payload=request.json,
        hail_initial_status=None,
        hail_final_status=hail.status,
        request_user=current_user,
        response_payload=ret,
        response_status_code=201
    )

    influx_backend.log_value('hails_created', {
        'added_by': current_user.email,
        'operator': hail_operateur_email,
        'zupc': taxi_ads_insee,
        'geohash': geohash2.encode(args['customer_lat'], args['customer_lon'])
    })

    return ret, 201
