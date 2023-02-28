"""
Tools to easily access Redis data and debug
"""
import json

import click
from flask import Blueprint, current_app
from flask.cli import with_appcontext

from APITaxi_models2 import Hail


blueprint = Blueprint('commands_redis', __name__, cli_group=None)


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
        body = json.loads(body)
        # When a hail is first logged at creation, the payloads are dicts
        # but then all subsequent payloads are logged as serialized
        if isinstance(body['payload'], str):
            body['payload'] = json.loads(body['payload'])
        if isinstance(body['return'], str):
            try:
                body['return'] = json.loads(body['return'])
            except json.JSONDecodeError:
                pass
        print(json.dumps(body, indent=2))
        print('---')
