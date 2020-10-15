from datetime import timedelta
import json

from flask import current_app
import requests
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from APITaxi_models2 import db, Hail, Taxi, Vehicle, VehicleDescription

from .. import redis_backend, schemas
from . import celery


@celery.task(name='handle_hail_timeout')
def handle_hail_timeout(hail_id, operateur_id,
                        initial_hail_status=None, new_hail_status=None,
                        new_taxi_status=None):
    """This task is called asynchronously. If hail status is still
    `initial_hail_status`, then we log a warning message and set the hail
    status to `new_hail_status` (required) and the taxi status to
    `new_taxi_status` (optional).
    """
    assert initial_hail_status
    assert new_hail_status

    res = db.session.query(
        Hail, VehicleDescription
    ).options(
        joinedload(Hail.taxi)
    ).filter(
        Hail.taxi_id == Taxi.id,
        Taxi.vehicle_id == Vehicle.id,
        VehicleDescription.vehicle_id == Vehicle.id,
        Hail.id == hail_id,
        VehicleDescription.added_by_id == operateur_id
    ).one_or_none()
    if not res:
        current_app.logger.error(
            'handle_hail_timeout: hail_id=%s operateur_id=%s not found',
            hail_id,
            operateur_id
        )
        return

    hail, vehicle_description = res

    # Hail status is different from the status which triggers the timeout.
    if hail.status != initial_hail_status:
        return

    error_msg = \
        f'Timeout occured: hail {hail_id} of taxi {hail.taxi_id} with operator' \
        f' {hail.added_by_id} still has status {initial_hail_status}. Set new hail' \
        f' status to {new_hail_status}'
    if new_taxi_status:
        error_msg += f' and taxi status to {new_taxi_status}'

    current_app.logger.warning(error_msg)

    hail.status = new_hail_status

    if new_taxi_status:
        vehicle_description.status = new_taxi_status

    db.session.commit()


@celery.task(name='send_request_operator')
def send_request_operator(hail_id, endpoint, operator_header_name, operator_api_key, operator_email):
    """Send the hail request to the operator's API.

    If this task is called with too much delay because of production issues,
    mark the hail as failed.
    """
    res = db.session.query(
        Hail, VehicleDescription
    ).options(
        joinedload(Hail.taxi)
    ).options(
        joinedload(Hail.added_by)
    ).options(
        joinedload(Hail.operateur)
    ).options(
        joinedload(Hail.customer)
    ).join(
        Taxi, Taxi.id == Hail.taxi_id
    ).join(
        Vehicle
    ).filter(
        Hail.taxi_id == Taxi.id,
        Taxi.vehicle_id == Vehicle.id,
        VehicleDescription.vehicle_id == Vehicle.id,
        Hail.id == hail_id
    ).one_or_none()
    if not res:
        current_app.logger.error('Unable to find hail %s' % hail_id)
        return False

    hail, vehicle_description = res

    if hail.status != 'received':
        current_app.logger.error('Task send_request_operator called for hail %s, but status is %s. Ignore.',
                                 hail.id, hail.status)
        return False

    if db.session.query(func.NOW() - hail.added_at).scalar() > timedelta(seconds=+10):
        current_app.logger.error(
            'Task send_request_operator called for hail %s after more than 10 seconds. Set as failure.',
            hail.id
        )
        hail.status = 'failure'
        db.session.commit()
        return False

    taxi_position = redis_backend.get_taxi(hail.taxi_id, hail.added_by.email)

    schema = schemas.WrappedHailSchema()
    payload = schema.dump({'data': [(hail, taxi_position)]})

    # Custom headers to send to operator's API.
    headers = {}
    if operator_header_name:
        headers[operator_header_name] = operator_api_key

    # Send request.
    try:
        resp = requests.post(endpoint, json=payload)
    # If operator's API is unavailable, log the error, set hail as failure and
    # abort.
    except requests.exceptions.RequestException as exc:
        current_app.logger.error('Unable to send request to operator %s on %s: %s' % (
            hail.operateur.email, endpoint, exc
        ))
        redis_backend.log_hail(
            hail_id=hail.id,
            http_method='POST to operator',
            request_payload=json.dumps(payload, indent=2),
            hail_initial_status=hail.status,
            request_user=None,
            response_payload=str(exc),
            response_status_code=None
        )
        hail.status = 'failure'
        db.session.commit()
        return False

    # Operator's API should return a JSON response. If it doesn't, log an
    # error, set hail as failure and abort.
    try:
        response_payload = json.dumps(resp.json(), indent=2)
    except json.decoder.JSONDecodeError:
        current_app.logger.error('Operator API of %s did not return a JSON response' % hail.operateur.email)
        redis_backend.log_hail(
            hail_id=hail.id,
            http_method='POST to operator',
            request_payload=json.dumps(payload, indent=2),
            hail_initial_status=hail.status,
            request_user=None,
            response_payload='Response should be valid JSON, but the API response was: %s' % resp.text,
            response_status_code=resp.status_code
        )
        hail.status = 'failure'
        db.session.commit()
        return False

    # If the operator's API isn't successful, log the response, set hail as
    # failure and abort.
    if resp.status_code < 200 or resp.status_code >= 300:
        current_app.logger.error('Operator API of %s returned HTTP/%s instead of HTTP/2xx' % (
            hail.operateur.email, resp.status_code
        ))
        redis_backend.log_hail(
            hail_id=hail.id,
            http_method='POST to operator',
            request_payload=json.dumps(payload, indent=2),
            hail_initial_status=hail.status,
            request_user=None,
            response_payload=response_payload,
            response_status_code=resp.status_code
        )
        hail.status = 'failure'
        db.session.commit()
        return False

    # Log this successful request
    current_app.logger.info('Successfully sent hail request to %s' % hail.operateur.email)
    redis_backend.log_hail(
        hail_id=hail.id,
        http_method='POST to operator',
        request_payload=json.dumps(payload, indent=2),
        hail_initial_status=hail.status,
        request_user=None,
        response_payload=response_payload,
        response_status_code=resp.status_code
    )

    # As all our API responses, the operator's API response is expected to be a
    # dictionary with one key, "data", which is a list of one element.
    #
    # If this is the case and the key "taxi_phone_number" is present, store the
    # phone number.
    #
    # According to our documentation, operators should provide the taxi's phone
    # number with a PUT request on /hails/:id, but some of them do not follow
    # the documentation and return the phone number here.
    data = resp.json()
    if isinstance(data, dict) and len(data.get('data', [])) >= 1 and 'taxi_phone_number' in data['data'][0]:
        hail.taxi_phone_number = data['data'][0]['taxi_phone_number']

    hail.status = 'received_by_operator'
    db.session.commit()

    # If hail is still "received_by_operator" and not "accepted_by_taxi" after 10 seconds, timeout.
    handle_hail_timeout.apply_async(
        args=(hail.id, vehicle_description.added_by_id),
        kwargs={
            'initial_hail_status': 'received_by_operator',
            'new_hail_status': 'failure',
        },
        countdown=10
    )

    return True
