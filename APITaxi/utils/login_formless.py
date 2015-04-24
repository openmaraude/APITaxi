# -*- coding: utf8 -*-
from flask.ext.security import LoginForm
from flask import request, abort
from functools import wraps

def login_formless(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        auth = request.authorization
        if not auth:
            abort(401)
        form = LoginForm(obj={"email":auth.username, "password": auth.password})
        if not form.validate():
            abort(403)
        return func(*args, **kwargs)
    return wrap

