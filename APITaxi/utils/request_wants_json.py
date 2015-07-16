# -*- coding: utf-8 -*-
#Source: http://flask.pocoo.org/snippets/45/

from flask.ext.restful import request, abort
from functools import wraps

def request_wants_json():
    best = request.accept_mimetypes \
        .best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] >= \
        request.accept_mimetypes['text/html']


def json_mimetype_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not request_wants_json():
            abort(400, message="You need to accept json to complete your request")
        return f(*args, **kwargs)
    return wrapper
