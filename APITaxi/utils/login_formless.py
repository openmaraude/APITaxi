# -*- coding: utf-8 -*-
from flask.ext.security import LoginForm
from flask import request
from flask.ext.restplus import abort
from functools import wraps

def login_formless(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        auth = request.authorization
        if not auth:
            abort(401, message="Unable to log you")
        form = LoginForm(obj={"email":auth.username, "password": auth.password})
        if not form.validate():
            abort(403, message="Form invalid")
        return func(*args, **kwargs)
    return wrap

