from flask import request, current_app
from flask_httpauth import HTTPTokenAuth
from werkzeug.local import LocalProxy

from APITaxi_models2 import Role, User

from . import activity_logs


auth = HTTPTokenAuth(scheme='', header='X-Api-Key')
auth.get_user_roles(lambda user: user.roles)
current_user = LocalProxy(lambda: auth.current_user())


@auth.verify_token
def verify_token(value):
    if value:
        user = User.query.filter_by(apikey=value).first()
        if user:
            logas_user = load_logas(user)
            if logas_user and request.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
                if logas_user.id != user.id:
                    activity_logs.log_user_auth_logas(
                        logas_user.id,
                        method=request.method,
                        location=request.path,
                        apikey_belongs_to=str(user.id),
                    )
                else:
                    activity_logs.log_user_auth_apikey(
                        user.id,
                        method=request.method,
                        location=request.path
                    )
            return logas_user
    return None


def load_user_from_api_key_header(request):
    """Callback to extract X-Api-Key header from the request and get user."""
    value = request.headers.get('X-Api-Key')
    return verify_token(value)


def load_logas(user):
    logas_email = request.headers.get('X-Logas')
    if logas_email:
        # Trying to log as yourself.
        if logas_email == user.email:
            return user

        query = User.query.filter_by(email=logas_email)

        # Administrators can log as any other user.
        if user.has_role('admin'):
            user = query.one_or_none()
        # If integration feature is enabled, logas is always possible for
        # integration user.
        elif (
            current_app.config.get('INTEGRATION_ENABLED')
            and current_app.config.get('INTEGRATION_ACCOUNT_EMAIL') == logas_email
        ):
            user = query.one_or_none()
        # Otherwise, logas is only possible if user is the manager.
        else:
            query = query.filter_by(manager=user)
            user = query.one_or_none()
    return user
