#coding: utf-8
from ..extensions import celery
from flask import current_app
from logging import getLogger

def init_app(app):
    celery.init_app(app)
from .make_views import store_active_taxis as f
from .clean_geoindex import clean_geoindex

@celery.task()
def store_active_taxis(frequency):
    return f(frequency)
