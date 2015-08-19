#coding: utf-8
from ..extensions import celery
from flask import current_app
from logging import getLogger

def init_app(app):
    celery.init_app(app)
from .make_views import store_active_taxis as f

@celery.task()
def store_active_taxis():
    return f()
