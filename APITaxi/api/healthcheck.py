from ..api import api
from flask_restplus import Resource
from APITaxi_models import db
from ..extensions import redis_store, redis_store_saved, celery
from sqlalchemy.exc import SQLAlchemyError
from redis import RedisError

ns_healthcheck = api.namespace(
    'healthcheck',
    description='Health checks'
)

@ns_healthcheck.route('/', endpoint='healthcheck')
class HealthCheck(Resource):
    def get(self):
        return {
            'healthchecks': {
                'postgresql': self.postgresql(),
                'redis': self.redis(),
                'redis-saved': self.redis_saved(),
                'celery': self.celery()
            },
            '_help': {
                'postgresql': 'Answer must be: \'[true, "ok"]\'',
                'redis': 'Answer must be: \'[true, "ok"]\'',
                'redis-saved': 'Answer must be: \'[true, "ok"]\'',
                'celery': 'Answer must be something like: \'[{\'celery@send_hail\': {\'ok\': \'pong\'}}, {\'celery@api.taxi\': {\'ok\': \'pong\'}}]\''
            }
        }
    
    def postgresql(self):
        """ Ensures database `engine` is available.
        """
        try:
            db.session.execute('SELECT 1').fetchone()
        except (IOError, SQLAlchemyError):
            return False, 'Unable to reach database'
        return True, 'ok'

    def redis(self):
        try:
            redis_store.ping()
        except RedisError:
            return False, 'Unable to reach redis'
        return True, 'ok'

    def redis_saved(self):
        try:
            redis_store_saved.ping()
        except RedisError:
            return False, 'Unable to reach redis saved'
        return True, 'ok'

    def celery(self):
        return celery.control.ping()

