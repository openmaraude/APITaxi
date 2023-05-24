"""Celery entrypoint.

To run the worker, call:

    (shell)> celery worker --app APITaxi2.celery_worker -E

To call a task manually:

    # Without arguments
    (shell)> celery call --app APITaxi2.celery_worker <task_name>
    # With arguments
    (shell)> celery call --app APITaxi2.celery_worker <task_name> --args=[1,2,3]
"""

from . import create_app

# Create flask application and configure Celery
flask_app = create_app()
celery_app = flask_app.extensions['celery']
# TODO remove
celery = celery_app
