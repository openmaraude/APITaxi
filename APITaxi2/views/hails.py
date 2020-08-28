from datetime import timedelta

from flask import Blueprint, request
from flask_principal import RoleNeed, Permission
from flask_security import current_user, login_required, roles_accepted

import sqlalchemy
from sqlalchemy.orm import joinedload

from APITaxi_models2 import db, Hail
from APITaxi_models2.hail import HAIL_TERMINAL_STATUS

from .. import redis_backend, schemas
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


def _set_hail_status(hail, new_status, new_taxi_phone_number):
    """Change `hail`'s status to `new_status`. Raises ValueError if the change
    is impossible.

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
            'incident_taxi': 'taxi',
        },
        'customer_on_board': {
            'finished': 'operateur',
        }
    }
    if hail.status in TRANSITIONS:
        if new_status not in TRANSITIONS[hail.status]:
            raise ValueError(f'Impossible to set status from {hail.status} to {new_status}')
        if (
            not current_user.has_role(TRANSITIONS[hail.status][new_status]) and
            not current_user.has_role('admin')
        ):
            raise ValueError(
                f'Permission {TRANSITIONS[hail.status][new_status]} is required to change status '
                f'from {hail.status} to {new_status}'
            )

    hail.status = new_status
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


def _ban_customer(customer):
    """Ban customer. Several cases:

    1. Customer is already flagged as banned:
        a) ban is finished: ban customer for 24 hours
        b) ban is still ongoing: double the ban time

    2. Customer is not flagged as banned: ban for 24 hours
    """
    # Case 1.
    if customer.ban_begin and customer.ban_end:
        ban_ongoing = db.session.query(customer.ban_end >= sqlalchemy.func.NOW()).scalar()
        # 1. a)
        if not ban_ongoing:
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
    hail = Hail.query.options(
        joinedload(Hail.taxi)
    ).options(
        joinedload(Hail.added_by)
    ).options(
        joinedload(Hail.operateur)
    ).options(
        joinedload(Hail.customer)
    ).get(hail_id)
    if not hail:
        return make_error_json_response({
            'url': ['Hail not found']
        }, status_code=404)
    if current_user not in (hail.operateur, hail.added_by) and not current_user.has_role('admin'):
        return make_error_json_response({
            'url': ['You do not have the permissions to view this hail']
        }, status_code=403)

    schema = schemas.data_schema_wrapper(schemas.HailSchema)()
    taxi_position = redis_backend.get_taxi(hail.taxi_id, hail.added_by.email)

    if request.method == 'GET':
        return schema.dump({'data': [(hail, taxi_position)]})

    params, errors = validate_schema(schema, request.json)
    if errors:
        return make_error_json_response(errors)

    args = request.json['data'][0]

    hail_initial_status = hail.status

    try:
        status_changed = _set_hail_status(hail, args.get('status', NOT_PROVIDED), args.get('taxi_phone_number'))
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
            request_payload=request.json,
            hail_initial_status=hail_initial_status,
            request_user=current_user,
            response_payload=ret,
            response_status_code=200
        )

    return ret
