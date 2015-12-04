DEBUG = True
SECRET_KEY = 'super-secret'
SQLALCHEMY_DATABASE_URI = 'postgresql://vincent:vincent@localhost/odtaxi_test'
REDIS_URL = "redis://:@localhost:6379/0"
REDIS_GEOINDEX = 'geoindex'
SQLALCHEMY_POOL_SIZE = 2


SECURITY_PASSWORD_HASH = 'plaintext'
NOW = 'time_test'
DOGPILE_CACHE_BACKEND = 'dogpile.cache.null'
