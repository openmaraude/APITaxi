"""Celery entrypoint.

To run the worker, call:

    (shell)> celery worker --app APITaxi2.celery_worker.celery -E

To call a task manually:

    # Without arguments
    (shell)> celery call --app APITaxi2.celery_worker.celery <task_name>
    # With arguments
    (shell)> celery call --app APITaxi2.celery_worker.celery <task_name> --args=[1,2,3]
"""

from . import create_app

# Create flask application and configure Celery
app = create_app()

from .tasks import celery  # noqa
