DEBUG = True
ENV = 'DEV'
SECRET_KEY = 'super-secret'
SQLALCHEMY_DATABASE_URI = 'postgresql://v:v@localhost/odtaxi'
REDIS_URL = "redis://:@localhost:6379/0"
REDIS_GEOINDEX = 'geoindex'
REDIS_TIMESTAMPS = 'timestamps'
REDIS_NOT_AVAILABLE = 'not_available'
SECURITY_PASSWORD_HASH = 'bcrypt'
SECURITY_PASSWORD_SALT = 'pepper'
SECURITY_REGISTERABLE = True
UPLOADED_IMAGES_DEST = 'uploads'

UPLOADED_DOCUMENTS_DEST = 'uploads'
UPLOADED_DOCUMENTS_URL = '/documents/<path:filename>'

SLACK_API_KEY = None

DOGPILE_CACHE_URLS = ''
DOGPILE_CACHE_REGIONS = [
    ('taxis', None,'dogpile.cache.null'),
    ('hails', None, 'dogpile.cache.null'),
    ('taxis_zupc', None, 'dogpile.cache.null'),
    ('taxis_cache_sql', None, 'dogpile.cache.null'),
    ('zupc', None, 'dogpile.cache.memory'),
    ('users', None, 'dogpile.cache.memory'),
    ('taxis_cache_sql', 5*60, 'dogpile.cache.null', None,
        {'wrap': 'APITaxi_utils.msgpack_backend.MsgpackProxy'}),
    ('zupc_lon_lat', None, 'dogpile.cache.memory')#, None,{'url': 'redis://localhost:6379/0'})
]

DOGPILE_CACHE_BACKEND = 'dogpile.cache.null'
DOGPILE_CACHE_URLS = ['redis://localhost:6379/0']
SQLALCHEMY_POOL_SIZE = 15
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['pickle']
CELERYBEAT_SCHEDULE_FILENAME  = '/tmp/celery_beat_schedule'

from celery.schedules import crontab
#List of tuples of the form
# (frequency in minute, kwargs) where kwargs in passed to crontab
STORE_TAXIS_FREQUENCIES = [(1, {'minute': '*/1'}),
    (60,{'minute': 0, 'hour': '*/1'}), (24*60, {'minute': 0, 'hour': 0})]
CELERYBEAT_SCHEDULE = dict([
    ('clean_timestamps',
        {'task': 'APITaxi.tasks.clean_timestamps',
         'schedule': crontab(minute='*/1'),
         }
    )
])
for frequency, cron_kwargs in STORE_TAXIS_FREQUENCIES:
    CELERYBEAT_SCHEDULE['store_active_taxis_every_{}'.format(frequency)] =  {
            'task': 'APITaxi.tasks.store_active_taxis',
            'schedule': crontab(**cron_kwargs),
            'args': [frequency]
    }


INFLUXDB_HOST = 'localhost'
INFLUXDB_PORT = 8086
INFLUXDB_USERNAME = ''
INFLUXDB_PASSWORD = ''
INFLUXDB_TAXIS_DB = 'taxis'
NOW = 'now'
LIMITED_ZONE = None
SQLALCHEMY_TRACK_MODIFICATIONS = True

SLACK_CHANNEL = "#taxis-internal"
