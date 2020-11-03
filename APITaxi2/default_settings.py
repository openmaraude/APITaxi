# SQLALCHEMY_ECHO = True

# Warning is displayed when SQLALCHEMY_TRACK_MODIFICATIONS is the default.
# Future SQLAlchemy version will set this value to False by default anyway.
SQLALCHEMY_TRACK_MODIFICATIONS = False

INFLUXDB_DATABASE = 'taxis'

CELERY_BEAT_SCHEDULE = {
    # Call clean_geoindex_timestamps every 10 minutes
    'clean-geoindex-timestamps': {
        'task': 'clean_geoindex_timestamps',
        'schedule': 60 * 10
    }
}
