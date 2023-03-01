from sqlalchemy import func, insert

from APITaxi_models2 import db
from APITaxi_models2.activity_logs import activity_log


RESOURCES = (
    'user',
    'taxi',
    'customer',
)

ACTION_LOGIN_PASSWORD = 'login_password'
ACTION_LOGIN_APIKEY = 'login_apikey'
ACTION_AUTH_APIKEY = 'auth_apikey'
ACTION_AUTH_LOGAS = 'auth_logas'
ACTION_TAXI_STATUS = 'taxi_status'
ACTION_CUSTOMER_HAIL = 'customer_hail'

ACTIONS = {
    ACTION_LOGIN_PASSWORD: "User logs in using the password (console)",
    ACTION_LOGIN_APIKEY: "User logs in using the API key (console)",
    ACTION_AUTH_APIKEY: "User authenticates using the API key",
    ACTION_AUTH_LOGAS: "User authenticates as another user",
    ACTION_TAXI_STATUS: "Taxi changed status",
    ACTION_CUSTOMER_HAIL: "Customer hails a taxi"
}


def _log_activity(resource, resource_id, action, **extra):
    assert resource in RESOURCES
    assert action in ACTIONS

    with db.engine.connect() as conn:
        stmt = insert(activity_log).values(
            time=func.now(),
            resource=resource,
            resource_id=resource_id,
            action=action,
            extra=extra,
        )
        conn.execute(stmt)


def log_user_login_password(user_id, **extra):
    """console login using email and password"""
    _log_activity('user', user_id, ACTION_LOGIN_PASSWORD, **extra)


def log_user_login_apikey(user_id, **extra):
    "console login using the apikey (user switch)"
    _log_activity('user', user_id, ACTION_LOGIN_APIKEY, **extra)


def log_user_auth_apikey(user_id, **extra):
    """authenticated method using the API key"""
    _log_activity('user', user_id, ACTION_AUTH_APIKEY, **extra)


def log_user_auth_logas(user_id, **extra):
    """authenticated method using the X-Logas header"""
    _log_activity('user', user_id, ACTION_AUTH_LOGAS, **extra)


def log_taxi_status(taxi_id, old_status, new_status, **extra):
    """taxi status changed (on the vehicle description)"""
    _log_activity('taxi', taxi_id, ACTION_TAXI_STATUS, old_status=old_status, new_status=new_status, **extra)


def log_customer_hail(customer_id, taxi_id, hail_id, **extra):
    """customer hailed a given taxi"""
    _log_activity('customer', customer_id, ACTION_CUSTOMER_HAIL, taxi_id=taxi_id, hail_id=hail_id, **extra)
