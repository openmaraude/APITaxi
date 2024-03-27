from datetime import datetime, timedelta
import json
import time
import uuid

from flask import Blueprint, request, current_app

from sqlalchemy import func, or_
from sqlalchemy.orm import aliased, joinedload

from APITaxi_models2 import Customer, db, Hail, Taxi, User, Vehicle, VehicleDescription
from APITaxi_models2.hail import HAIL_TERMINAL_STATUS

from .. import activity_logs, redis_backend, schemas, tasks, processes, utils
from ..security import auth, current_user
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


blueprint = Blueprint('hails', __name__)


def _get_short_uuid():
    return str(uuid.uuid4())[0:7]


def _set_hail_status(hail, vehicle_description, new_status, new_taxi_phone_number, user):
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

    processes.change_status(hail, new_status, user=user)

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
        old_taxi_status = vehicle_description.status
        vehicle_description.status = new_taxi_status[new_status]
        activity_logs.log_taxi_status(
            hail.taxi_id,
            old_taxi_status,
            new_taxi_status[new_status],
            hail_id=hail.id,
        )

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

    res = db.session.query(customer.ban_end >= func.NOW()).scalar()
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
            customer.ban_begin = func.NOW()
            customer.ban_end = func.NOW() + timedelta(hours=+24)
        # 1. b)
        else:
            ban_duration = customer.ban_end - customer.ban_begin
            customer.ban_end = customer.ban_end + ban_duration
    # Case 2
    else:
        customer.ban_begin = func.NOW()
        customer.ban_end = func.NOW() + timedelta(hours=+24)


def _check_session_id(operator, customer, session_id):
    """Check if the UUID `session_id` is related to an existing session of
    `operator`'s `customer`.

    Raise ValueError if session id does not exist, or if it is linked to
    another operator's customer.
    """
    res = db.session.query(
        Hail.session_id, Hail.customer_id
    ).filter(
        Hail.session_id == session_id,
        Hail.added_by == operator,
    ).order_by(
        Hail.last_status_change.desc()
    ).first()

    if not res:
        raise ValueError('This sesssion ID does not exist.')

    prev_session_id, prev_customer_id = res
    if prev_customer_id != customer.id:
        raise ValueError('The session ID exists, but it is linked to another customer.')


def _get_existing_session_id(operator, customer):
    """If the `customer` of `operator` made a Hail request a few minutes ago,
    return the session id of this request. Otherwise, return None.
    """
    res = db.session.query(
        Hail.session_id
    ).filter(
        Hail.customer == customer,
        Hail.added_by == operator,
        Hail.last_status_change >= func.now() - timedelta(minutes=5)
    ).order_by(
        Hail.last_status_change.desc()
    ).first()

    if not res:
        return None
    return res[0]


@blueprint.route('/hails/<string:hail_id>', methods=['GET', 'PUT'])
@auth.login_required(role=['admin', 'moteur', 'operateur'])
def hails_details(hail_id):
    """
    ---
    get:
      tags:
        - both
      summary: Get hail details.
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
          description: |
            Return hail details.

            Note: the value of the field customer_phone_number is only shown when the customer has accepted their hail request,
            until they are declared on board.
          content:
            application/json:
              schema: DataHailSchema

    put:
      tags:
        - both
      summary: Edit hail details.
      description: |
        Mostly for updating the field `status` for the time of the fare, until it's `finished`.

        Besides the normal course of a fare, operators can:
        - declare an incident preventing the hail from properly finishing;
        - report a customer with inappropriate behavior.
        
        Similarly, customer apps can:
        - update the customer's position, address, and phone number;
        - declare an incident preventing the hail from properly finishing.

        **Declaring an incident from the operator side:**
        A hail can be prematurely ended with sending the field `status` with the value `incident_taxi`.
        The operator can send the reason by sending the field `incident_taxi_reason`
        with one of the accepted values in the schema below (in the same call, or a consecutive call).

        **Reporting a customer:**
        The customer with inappropriate behavior on this hail can be reported
        by the operator with sending the field `reporting_customer` with a true value,
        and the field `reporting_customer_reason` with one of the accepted values.
        This will prevent them from hailing for the next 24 hours.
        The ban can be cancelled with a false value.

        **Declaring an incident from the customer side:**
        A hail can be prematurely ended with sending the field `status` with the value `incident_customer`.
        The customer app can send the reason by sending the field `incident_customer_reason`
        with one of the accepted values in the schema below (in the same call, or a consecutive call).

        Fields editable by operators or customer apps, or both, are tagged in the schema below.
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
            examples:
                status:
                    summary: Change status
                    value:
                        {
                            "data": [
                                {
                                    "status": "customer_on_board"
                                }
                            ]
                        }
                report_customer:
                    summary: Report customer (operator)
                    value:
                        {
                            "data": [
                                {
                                    "reporting_customer": true,
                                    "reporting_customer_reason": "no_show"
                                }
                            ]
                        }
                incident_taxi:
                    summary: Declare an incident (reason is optional, see next example)
                    value:
                        {
                            "data": [
                                {
                                    "status": "incident_taxi"
                                }
                            ]
                        }
                incident_taxi_reason:
                    summary: Reason for status "incident_taxi" after the fact
                    value:
                        {
                            "data": [
                                {
                                    "incident_taxi_reason": "no_show"
                                }
                            ]
                        }
                accepted_by_taxi:
                    summary: Taxi to accept a hail request. The taxi must give their phone number to accept the hail.
                    value:
                        {
                            "data": [
                                {
                                    "status": "accepted_by_taxi",
                                    "taxi_phone_number": "0678901234"
                                }
                            ]
                        }
      security:
        - ApiKeyAuth: []
      responses:
        200:
          description: Return updated hail.
          content:
            application/json:
              schema: DataHailSchema
    """
    query = db.session.query(
        Hail, VehicleDescription
    ).options(
        joinedload(Hail.taxi).joinedload(Taxi.vehicle),
        joinedload(Hail.taxi).joinedload(Taxi.driver),
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
    )
    # Hails can't be accessed after two months
    if not current_user.has_role('admin'):
        query = query.filter(
            Hail.added_at >= (datetime.now() - timedelta(days=60))
        )
    query = query.one_or_none()
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
        return schema.dump({'data': [(hail, taxi_position, vehicle_description)]})

    params, errors = validate_schema(schema, request.json, partial=True)
    if errors:
        return make_error_json_response(errors)

    args = params.get('data', [{}])[0]

    hail_initial_status = hail.status

    try:
        status_changed = _set_hail_status(
            hail,
            vehicle_description,
            args.get('status', NOT_PROVIDED),
            args.get('taxi_phone_number'),
            current_user,
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
    if operateur_changes:
        hail.last_update_at = func.NOW()
    if error:
        return error

    # Same for customer fields.
    moteur_changes, error = _set_hail_values(
        hail,
        [
            'customer_lon',
            'customer_lat',
            'customer_address',
            'rating_ride',
            'rating_ride_reason',
            'incident_customer_reason'
        ],
        args,
        hail.added_by == current_user or current_user.has_role('admin')
    )
    if moteur_changes:
        hail.last_update_at = func.NOW()
    if error:
        return error

    # If reporting_customer is provided and different from the previous value,
    # ban or unban the customer depending on the new value.
    if 'reporting_customer' in operateur_changes:
        if not hail.reporting_customer:
            _unban_customer(hail.customer)
        else:
            _ban_customer(hail.customer)

    ret = schema.dump({'data': [(hail, taxi_position, vehicle_description)]})

    vehicle_description_added_by_id = vehicle_description.added_by_id

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
                args=(hail.id, vehicle_description_added_by_id),
                kwargs={
                    'initial_hail_status': 'received_by_taxi',
                    'new_hail_status': 'timeout_taxi',
                    'new_taxi_status': 'off'
                },
                countdown=30
            )
        # Hail has been accepted by the taxi. Customer has 20 seconds to accept
        # or refuse the hail. If not, hail becomes "timeout_customer" and taxi
        # is free again.
        elif hail.status == 'accepted_by_taxi':
            tasks.operators.handle_hail_timeout.apply_async(
                args=(hail.id, vehicle_description_added_by_id),
                kwargs={
                    'initial_hail_status': 'accepted_by_taxi',
                    'new_hail_status': 'timeout_customer',
                    'new_taxi_status': 'free'
                },
                countdown=30
            )
        # Hail is accepted by customer. Taxi has 30 minutes to pickup the
        # customer and change status to customer_on_board.
        elif hail.status == 'accepted_by_customer':
            tasks.operators.handle_hail_timeout.apply_async(
                args=(hail.id, vehicle_description_added_by_id),
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
                args=(hail.id, vehicle_description_added_by_id),
                kwargs={
                    'initial_hail_status': 'customer_on_board',
                    'new_hail_status': 'timeout_taxi',
                    'new_taxi_status': 'off'
                },
                countdown=60 * 60 * 2
            )
    return ret


@blueprint.route('/hails/', methods=['GET'])
@auth.login_required(role=['admin', 'moteur', 'operateur'])
def hails_list():
    """Returns the list of hails paginated.

    Accept querystring arguments ?p, ?id, ?status, ?date, ?operateur,
    ?operateur and ?taxi_id.

    Pagination is returned in the "meta" field.
    ---
    get:
      tags:
        - both
      summary: List hails.
      parameters:
        - in: query
          schema: ListHailsQuerystringSchema
      security:
        - ApiKeyAuth: []
      responses:
        200:
          description: List of hails.
          content:
            application/json:
              schema: DataHailListSchema
    """
    querystring_schema = schemas.ListHailsQuerystringSchema()
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

    # Filter on querystring arguments, partial match.
    for qname, field in (
        ('id', Hail.id),
        ('operateur', operateur_table.email),
        ('moteur', moteur_table.email),
        ('taxi_id', Hail.taxi_id),
        ('customer_id', Hail.customer_id),
    ):
        if qname not in querystring:
            continue
        if qname == 'operateur' and not current_user.has_role('admin'):
            continue
        query = query.filter(or_(*[
            func.lower(field).startswith(value.lower()) for value in querystring[qname]
        ]))

    # Filter on querystring arguments, exact match.
    for qname, field in (
        ('status', Hail.status),
        ('date', func.date(Hail.added_at)),
    ):
        if qname not in querystring:
            continue
        query = query.filter(or_(*[
            field == value for value in querystring[qname]
        ]))

    # Hails can't be accessed after two months
    if not current_user.has_role('admin'):
        query = query.filter(
            Hail.added_at >= (datetime.now() - timedelta(days=60))
        )

    # Order by date
    query = query.order_by(Hail.added_at.desc())

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
@auth.login_required(role=['admin', 'moteur'])
def hails_create():
    """
    ---
    post:
      tags:
        - client
      summary: Create a hail request.
      requestBody:
        content:
          application/json:
            schema: DataCreateHailSchema
            example:
                {
                    "data": [
                        {
                            "customer_id": "abc123",
                            "customer_lon": 2.35,
                            "customer_lat": 48.86,
                            "customer_address": "25 rue Quincampoix 75004 Paris",
                            "customer_phone_number": "0678901234",
                            "taxi_id": "GEzgkJIO",
                            "operateur": "neotaxi"
                        }
                    ]
                }
      security:
        - ApiKeyAuth: []
      responses:
        201:
          description: |
            Return the created hail.

            Note: the value of the field customer_phone_number is only shown when the customer has accepted their hail request,
            until they are declared on board.
          content:
            application/json:
              schema: DataHailSchema
    """
    schema = schemas.DataCreateHailSchema()
    params, errors = validate_schema(schema, request.json)
    if errors:
        return make_error_json_response(errors)

    args = params['data'][0]

    if current_app.config.get('FAKE_TAXI_ID'):
        real_taxi_id = redis_backend.get_real_taxi_id(current_user, args['taxi_id'])
    else:
        real_taxi_id = args['taxi_id']

    # Get taxi registered with the operateur, or return HTTP/404
    res = db.session.query(
        Taxi,
        VehicleDescription
    ).options(
        joinedload(Taxi.ads),
        joinedload(Taxi.vehicle),
        joinedload(Taxi.driver),
        joinedload(VehicleDescription.added_by)
    ).join(
        User,
        VehicleDescription.added_by_id == User.id
    ).filter(
        VehicleDescription.vehicle_id == Taxi.vehicle_id,
        # Instead of asking which operateur is using the given taxi ID, we can deduce it ourselves
        # taxi IDs are already unique, but vehicle descriptions are not for a given vehicle ID
        # This is all caused by our insanely complex vehicle model
        VehicleDescription.added_by_id == Taxi.added_by_id,
        Taxi.id == real_taxi_id,
    ).one_or_none()
    if not res:
        return make_error_json_response({
            'data': {
                '0': {
                    # Don't change it just in case it breaks anything
                    'operateur': ['Unable to find taxi for this operateur.']
                }
            }
        }, status_code=404)

    taxi, vehicle_description = res

    # Get or create Customer object
    customer = Customer.query.filter_by(added_by=current_user, id=args['customer_id']).one_or_none()
    if not customer:
        customer = Customer(
            id=args['customer_id'],

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

    # Compute or reuse a session ID for the current user
    session_id = args.get('session_id')
    if session_id:
        try:
            _check_session_id(current_user, customer, session_id)
        except ValueError as exc:
            return make_error_json_response({
                'data': {
                    '0': {
                        'session_id': [str(exc)]
                    }
                }
            })
    else:
        session_id = _get_existing_session_id(current_user, customer)

    # If no address was given (may happen with web apps), deduce it from reverse geocoding
    # at the risk of being wrong, but you should have sent the good address then.
    if not args['customer_address']:
        args['customer_address'] = utils.reverse_geocode(args['customer_lon'], args['customer_lat'])
        if not args['customer_address']:
            return make_error_json_response({
                'data': {
                    '0': {
                        'customer_address': ["Customer can't be located, please provide an pickup address for the taxi."]
                    }
                }
            })


    hail = Hail(
        id=_get_short_uuid(),
        creation_datetime=func.NOW(),
        taxi=taxi,
        status=None,
        last_status_change=func.NOW(),
        customer=customer,
        customer_lat=args['customer_lat'],
        customer_lon=args['customer_lon'],
        operateur=vehicle_description.added_by,
        customer_address=args['customer_address'],
        customer_phone_number=args['customer_phone_number'],
        initial_taxi_lon=taxi_position.lon,
        initial_taxi_lat=taxi_position.lat,
        fake_taxi_id=args['taxi_id'],
        session_id=session_id,

        added_by=current_user,
        added_via='api',
        added_at=func.NOW(),
        source='added_by',
        last_update_at=func.NOW(),
    )
    processes.change_status(hail, 'received', user=current_user)
    db.session.add(hail)
    db.session.flush()

    vehicle_description.status = 'answering'

    # A dedicated schema was used to create
    full_schema = schemas.DataHailSchema()
    ret = full_schema.dump({'data': [(hail, taxi_position, vehicle_description)]})

    hail_endpoint_production = hail.operateur.hail_endpoint_production
    operator_header_name = hail.operateur.operator_header_name
    operator_api_key = hail.operateur.operator_api_key

    activity_logs.log_customer_hail(customer.id, taxi.id, hail.id)

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

    return ret, 201
