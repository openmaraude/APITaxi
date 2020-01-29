from APITaxi.api import api
from APITaxi.tasks import task_healthchecks
from APITaxi_utils.healthchecks import all_healthchecks

from flask import current_app
from flask_restplus import Resource

ns_healthchecks = api.namespace(
    'healthchecks',
    description='Health checks'
)

@ns_healthchecks.route('/', endpoint='healthcheck')
class HealthChecks(Resource):
    def get(self):
        return {
            'healthchecks': all_healthchecks(),
            '_help': {
                'postgresql': 'Answer must be: \'[true, "ok"]\'',
                'redis': 'Answer must be: \'[true, "ok"]\'',
                'redis-saved': 'Answer must be: \'[true, "ok"]\'',
                'celery': 'Answer must be something like: \'[{\'celery@send_hail\': {\'ok\': \'pong\'}}, {\'celery@api.taxi\': {\'ok\': \'pong\'}}]\'',
                'worker_healthchecks': 'Same as above but executed on the worker'
            }
        }
