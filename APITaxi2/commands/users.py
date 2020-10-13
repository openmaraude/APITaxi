import uuid

import click
from flask import Blueprint, current_app
from flask.cli import with_appcontext
from flask_security.utils import hash_password

from APITaxi_models2 import db, Role, User


blueprint = Blueprint('commands_users', __name__, cli_group=None)


@with_appcontext
def valid_role(value):
    roles = [role.name for role in Role.query.with_entities(Role.name).all()]
    if value not in roles:
        raise click.BadParameter('Valid values are: %s' % ', '.join(roles))
    return value


@blueprint.cli.command('create_user')
@click.argument('email')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
@click.argument('roles', nargs=-1, required=True, type=valid_role)
def create_user(email, password, roles):
    user = User.query.filter_by(email=email).one_or_none()
    if user:
        current_app.logger.error('User already exists')
        return

    hashed_password = hash_password(password)

    user = User(
        email=email,
        password=hashed_password,
        commercial_name=email,
        apikey=str(uuid.uuid4()),
        active=True
    )
    db.session.add(user)
    db.session.flush()

    # Create a set, which removes duplicates.
    roles = set(roles)
    # Administrators should have the explicit permissions moteur and operateur.
    if 'admin' in roles:
        roles = roles.union({'moteur', 'operateur'})

    for rolename in roles:
        role = Role.query.filter_by(name=rolename).one()
        user.roles.append(role)

    db.session.commit()
