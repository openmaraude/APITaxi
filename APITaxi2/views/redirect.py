"""Backward compatibility: in the past, APITaxi was deployed on a dedicated
server and nginx was configured to redirect / to the console, and /doc to
swagger.

Now, the infrastructure is deployed on CleverCloud. We need to perform these
redirections here, since it is impossible to perform redirections on
CleverCloud's loadbalancers.
"""

from flask import Blueprint, current_app, redirect


blueprint = Blueprint('index', __name__)


@blueprint.route('/', methods=['GET'])
def index():
    url = current_app.config.get('CONSOLE_URL')
    return redirect(url, code=301)


@blueprint.route('/doc', methods=['GET'])
def doc():
    url = current_app.config.get('SWAGGER_URL')
    return redirect(url, code=301)
