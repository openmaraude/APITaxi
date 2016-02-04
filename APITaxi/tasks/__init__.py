#coding: utf-8
from ..extensions import celery

def init_app(app):
    celery.init_app(app)
from .make_views import store_active_taxis as f
from .clean_geoindex import clean_geoindex
from .send_request_operator import send_request_operator
from .clean_timestamps import clean_timestamps

@celery.task()
def store_active_taxis(frequency):
    return f(frequency)
