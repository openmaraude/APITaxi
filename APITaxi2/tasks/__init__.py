from celery import Celery

celery = Celery(__name__)

from .clean import clean_geoindex_timestamps
