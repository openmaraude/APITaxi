# -*- coding: utf-8 -*-
from .. import db
from ..models import security
from flask.ext.security import Security, SQLAlchemyUserDatastore
from flask.ext.security.utils import verify_and_update_password

user_datastore = SQLAlchemyUserDatastore(db, security.User,
                            security.Role)

def load_user_from_request(request):
    apikey = request.headers.environ.get('HTTP_X_API_KEY', None)
    if apikey:
        u = security.get_user_from_api_key(apikey)
        return u.first() or None
    auth = request.headers.get('Authorization')
    if not auth or auth.count(':') != 1:
        return None
    login, password = auth.split(':')
    user = user_datastore.get_user(login.strip())
    if user is None:
        return None
    if not verify_and_update_password(password.strip(), user):
        return None
    if not user.is_active():
        return None
    return user

def init_app(app):
    security = Security()
    security.init_app(app, user_datastore)
    app.login_manager.request_loader(load_user_from_request)
