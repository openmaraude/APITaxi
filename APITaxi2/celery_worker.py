"""Celery entrypoint.

To run the worker, call:

    (shell)> celery worker --app APITaxi2.celery_worker.celery -E

To call a task manually:

    (shell)> celery call --app APITaxi2.celery_worker.celery <task_name>
"""

from APITaxi2 import create_app

# Create flask application and configure Celery
app = create_app()

from APITaxi2.tasks import celery
