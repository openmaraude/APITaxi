# SQLALCHEMY_ECHO = True

# Warning is displayed when SQLALCHEMY_TRACK_MODIFICATIONS is the default.
# Future SQLAlchemy version will set this value to False by default anyway.
SQLALCHEMY_TRACK_MODIFICATIONS = False

INFLUXDB_DATABASE = 'taxis'
INFLUXDB_CREATE_DATABASE = False

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
}

SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True
}
