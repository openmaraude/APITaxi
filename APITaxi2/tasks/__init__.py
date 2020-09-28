from celery import Celery

celery = Celery(__name__)

from .clean import clean_geoindex_timestamps
from .send_request_operator import send_request_operator
