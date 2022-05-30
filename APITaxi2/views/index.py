from flask import Blueprint, current_app, redirect


blueprint = Blueprint('index', __name__)


@blueprint.route('/', methods=['GET'])
def index():
    """For backward compatibility, / redirects to the console."""
    url = current_app.config.get('CONSOLE_URL')
    return redirect(url, code=301)
