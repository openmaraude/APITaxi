from APITaxi.api import api
from APITaxi.tasks import task_healthchecks
from APITaxi_utils.healthchecks import all_healthchecks, status

from flask import current_app
from flask_restplus import Resource

ns_healthchecks = api.namespace(
    'healthchecks',
    description='Health checks'
)

@ns_healthchecks.route('/', endpoint='healthcheck')
class HealthChecks(Resource):
    def get(self):
        checks = all_healthchecks()
        return {
            'status': status(checks),
            'checks': {k: v[1] for k, v in all_healthchecks().items()},
        }
