#coding: utf-8
from ..extensions import celery

def init_app(app):
    celery.init_app(app)
from .make_views import store_active_taxis
from .clean_geoindex_timestamps import clean_geoindex_timestamps
from .send_request_operator import send_request_operator
