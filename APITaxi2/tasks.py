from celery import Celery
from flask import current_app


celery = Celery(__name__)
