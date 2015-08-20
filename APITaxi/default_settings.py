DEBUG = True
ENV = 'DEV'
SECRET_KEY = 'super-secret'
SQLALCHEMY_DATABASE_URI = 'postgresql://v:v@localhost/odtaxi'
REDIS_URL = "redis://:@localhost:6379/0"
REDIS_GEOINDEX = 'geoindex'
SECURITY_PASSWORD_HASH = 'bcrypt'
SECURITY_PASSWORD_SALT = 'pepper'
SECURITY_REGISTERABLE = True
UPLOADED_IMAGES_DEST = '/home/vincent/dev/APITaxi/uploads'

UPLOADS_DOCUMENTS_DEST = 'uploads'
UPLOADS_DOCUMENTS_URL = '/documents/<path:filename>'

SLACK_API_KEY = None

DOGPILE_CACHE_URLS = ''
DOGPILE_CACHE_REGIONS = [
    ('taxis', None)
]

DOGPILE_CACHE_BACKEND = 'dogpile.cache.memory'
SQLALCHEMY_POOL_SIZE = 15

CELERYBEAT_SCHEDULE = {
    'store_active_taxis': {
        'task': 'APITaxi.tasks.store_active_taxis',
        'schedule': crontab(minute='*/15'),
    }
}

INFLUXDB_HOST = 'localhost'
INFLUXDB_PORT = 8086
INFLUXDB_USER = ''
INFLUXDB_PASSWORD = ''
INFLUXDB_TAXIS_DB = ''
