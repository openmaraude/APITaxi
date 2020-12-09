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


@with_appcontext
def user_exists(value):
    """Returns True if user exists."""
    if not User.query.filter_by(email=value).count():
        raise click.BadParameter('User %s does not exist' % value)
    return value


@blueprint.cli.command('create_user')
@click.argument('email')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
@click.argument('roles', nargs=-1, required=False, type=valid_role)
def create_user(email, password, roles):
    user = User.query.filter_by(email=email).one_or_none()
    if user:
        current_app.logger.info('User already exists, abort.')
        return

    if not roles and not click.confirm('No role specified for user. Continue?'):
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


@blueprint.cli.command('update_password', help='Update user password')
@click.argument('email')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
def update_password(email, password):
    user = User.query.filter_by(email=email).one_or_none()
    if not user:
        current_app.logger.info('User does not exist, abort.')
        return

    user.password = hash_password(password)

    db.session.commit()


@blueprint.cli.command('set_manager', help='Set account as manager of other accounts')
@click.argument('manager_account', type=user_exists)
@click.argument('managed_accounts', nargs=-1, required=True, type=user_exists)
def set_manager(manager_account, managed_accounts):
    manager = User.query.filter_by(email=manager_account).one()

    for user in User.query.filter(User.email.in_(managed_accounts)):
        if user.manager_id != manager.id:
            current_app.logger.info('Set user %s manager of user %s', manager.id, user.id)
            user.manager_id = manager.id
    db.session.commit()


@blueprint.cli.command('remove_manager', help='Remove manager from account')
@click.argument('managed_accounts', nargs=-1, required=True, type=user_exists)
def remove_manager(managed_accounts):
    for user in User.query.filter(User.email.in_(managed_accounts)):
        if user.manager_id:
            current_app.logger.info('Removing manager user %s from user %s', user.manager_id, user.id)
            user.manager_id = None
    db.session.commit()
