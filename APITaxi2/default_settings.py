import os

from celery.schedules import crontab
from flask_security.utils import uia_username_mapper


# SQLALCHEMY_ECHO = True

# Warning is displayed when SQLALCHEMY_TRACK_MODIFICATIONS is the default.
# Future SQLAlchemy version will set this value to False by default anyway.
SQLALCHEMY_TRACK_MODIFICATIONS = False

_ONE_MINUTE = 60
_ONE_HOUR = _ONE_MINUTE * 60
_ONE_DAY = _ONE_HOUR * 24
_SEVEN_DAYS = _ONE_DAY * 7

CELERY_BEAT_SCHEDULE = {
    'clean-geoindex-timestamps': {
        'task': 'clean_geoindex_timestamps',
        # Every 10 minutes
        'schedule': _ONE_MINUTE * 10
    },

    # Every minute, store the list of taxis available the last minute.
    'store-active-taxis-last-minute': {
        'task': 'store_active_taxis',
        'schedule': _ONE_MINUTE,
        'args': (1,),
    },

    # Every hour, store the list of taxis available the last hour.
    'store-active-taxis-last-hour': {
        'task': 'store_active_taxis',
        'schedule': _ONE_HOUR,
        'args': (60,)
    },

    # Every day, store the list of taxis available the last day.
    'store-active-taxis-last-day': {
        'task': 'store_active_taxis',
        'schedule': _ONE_DAY,
        'args': (1440,)
    },

    # Every day, store the list of taxis available the last 7 days.
    'store-active-taxis-last-seven-days': {
        'task': 'store_active_taxis',
        'schedule': _ONE_DAY,
        'args': (10080,)
    },

    # crontab

    'blur-geotaxi': {
        'task': 'blur_geotaxi',
        'schedule': crontab(hour=4, minute=0),
    },
    'blur-hails': {
        'task': 'blur_hails',
        'schedule': crontab(hour=4, minute=2),
    },
    'delete-old-hails': {
        'task': 'delete_old_hails',
        'schedule': crontab(hour=4, minute=4),
    },
    'delete-old-taxis': {
        'task': 'delete_old_taxis',
        'schedule': crontab(hour=4, minute=6),
    },
    'delete-old-orphans': {
        'task': 'delete_old_orphans',
        'schedule': crontab(hour=4, minute=8),
    },
    'compute-stats-hails': {
        'task': 'compute_stats_hails',
        'schedule': crontab(hour=4, minute=10),
    },
}

SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True
}


# Flask-Security-Too introduced email validation, but we use the email field as a username
SECURITY_USER_IDENTITY_ATTRIBUTES = [
    {"email": {"mapper": uia_username_mapper, "case_insensitive": True}}
]


def parse_env_bool(value):
    """Convert the string value to a boolean."""
    if value is None:
        return None
    elif value.lower() in ('yes', 'true', '1', 't'):
        return True
    elif value.lower() in ('no', 'false', '0', 'f', ''):
        return False
    raise ValueError(f'Invalid boolean value "{value}" in environment')


# The following code reads environment to create settings.
#
# The first entry of the list is the name of the setting to create, and also
# the name of the environment variable to get the value from.
#
# The second entry is an optional alternative name. It is used to deploy on
# clevercloud, where it is not possible to rename variables exposed by addons.
#
# The "algorithm" works as follow, for example for SQLALCHEMY_DATABASE_URI:
# - if the environment variable SQLALCHEMY_DATABASE_URI is set, create a global
#   variable named SQLALCHEMY_DATABASE_URI with it's value.
# - otherwise, create a global variable SQLALCHEMY_DATABASE_URI with the value of
#   the environment variable POSTGRESQL_ADDON_URI.
# - if both the environment variable and the alternative name exist,
#   the alternative name has priority. So REDIS_URL will be overwritten by
#   REDIS_DIRECT_URI if defined (for cloud hosting).
#   
for _env_var, _alt_name, _env_type in (
    ('DEBUG', None, parse_env_bool),
    ('SERVER_NAME', None, str),
    ('INTEGRATION_ENABLED', None, parse_env_bool),
    ('INTEGRATION_ACCOUNT_EMAIL', None, str),
    ('GEOTAXI_HOST', None, str),
    ('GEOTAXI_PORT', None, int),
    ('SECRET_KEY', None, str),
    ('SQLALCHEMY_DATABASE_URI', 'POSTGRESQL_ADDON_DIRECT_URI', str),
    ('REDIS_URL', 'REDIS_DIRECT_URI', str),
    ('SECURITY_PASSWORD_SALT', None, str),
    ('CELERY_BROKER_URL', 'REDIS_DIRECT_URI', str),
    ('CELERY_RESULT_BACKEND', 'REDIS_DIRECT_URI', str),
    ('SENTRY_DSN', None, str),
    ('SENTRY_SAMPLE_RATE', None, float),
    ('CONSOLE_URL', None, str),
    ('SWAGGER_URL', None, str),
    ('NEUTRAL_OPERATOR', None, parse_env_bool),
    ('FAKE_TAXI_ID', None, parse_env_bool),
):
    _val = os.getenv(_alt_name) if _alt_name else os.getenv(_env_var)
    if not _val:
        continue

    globals()[_env_var] = _env_type(_val)
