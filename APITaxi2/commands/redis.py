"""
Tools to easily access Redis data and debug
"""
import json

import click
from flask import Blueprint, current_app
from flask.cli import with_appcontext

from APITaxi2.utils import get_short_uuid
from APITaxi_models2 import db, Hail, User, Customer


blueprint = Blueprint('commands_redis', __name__, cli_group=None)


def _decode_body(body):
    """When a hail is first logged at creation, the payloads are dicts
    but then all subsequent payloads are logged as serialized"""
    body = json.loads(body)
    if isinstance(body['payload'], str):
        body['payload'] = json.loads(body['payload'])
    if isinstance(body['return'], str):
        try:
            body['return'] = json.loads(body['return'])
        except json.JSONDecodeError:
            pass
    return body


@with_appcontext
def hail_exists(value):
    """Validates hail ID."""
    if not Hail.query.filter_by(id=value).count():
        raise click.BadParameter('Hail %s does not exist' % value)
    return value


@blueprint.cli.command()
@click.argument('hail_id', required=True, type=hail_exists)
def dump_hail(hail_id):
    for body in current_app.redis.zrange(f'hail:{hail_id}', 0, -1):
        body = _decode_body(body)
        print(json.dumps(body, indent=2))
        print('---')


@with_appcontext
def hail_not_exists(value):
    """Validates hail ID not already taken."""
    if Hail.query.filter_by(id=value).count():
        raise click.BadParameter('Hail %s already exists' % value)
    return value


@blueprint.cli.command()
@click.argument('hail_id', required=True, type=hail_not_exists)
def restore_hail(hail_id):
    body = current_app.redis.zrange(f'hail:{hail_id}', -1, -1)[0]
    body = _decode_body(body)
    data = body['return']['data'][0]
    moteur_id = db.session.query(Customer.added_by_id).filter(Customer.id == data['customer_id']).scalar()
    operateur_id = db.session.query(User.id).filter(User.email == data['operateur']).scalar()
    hail = Hail(
        id=hail_id,
        creation_datetime=data['creation_datetime'],
        taxi_id=data['taxi']['id'],
        status=data['status'],
        last_status_change=data['last_status_change'],
        customer_id=data['customer_id'],
        customer_lat=data['customer_lat'],
        customer_lon=data['customer_lon'],
        operateur_id=operateur_id,
        customer_address=data['customer_address'],
        customer_phone_number=data['customer_phone_number'],
        initial_taxi_lon=data['customer_lon'],  # whatever
        initial_taxi_lat=data['customer_lat'],
        fake_taxi_id=get_short_uuid(),
        session_id=data['session_id'],
        added_by_id=moteur_id,
        added_via='api',
        added_at=data['creation_datetime'],
        source='added_by',
        last_update_at=data['last_status_change'],
        transition_log=data['transitions'],
    )
    db.session.add(hail)
    db.session.commit()
