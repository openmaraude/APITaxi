#!/usr/bin/env python
#coding: utf-8
import os
from APITaxi import create_app
from APITaxi.extensions import celery

app = create_app()
app.app_context().push()
