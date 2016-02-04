# -*- coding: utf-8 -*-
from flask.ext.security import Security
from flask.ext.security.utils import verify_and_update_password
from flask.ext.login import login_user, user_logged_out

def invalidate_user(sender, user, **extra):
    c = user.cache
    c.flush(c._cache_key(user.id))
    c.flush(c._cache_key(unicode(user.id)))
    c.flush(c._cache_key(**{"email":user.email}))
    c.flush(c._cache_key(**{"apikey":user.apikey}))

def init_app(app, user_datastore, LoginForm):
    def load_user(user_id):
        return user_datastore.get_user(user_id)

    def load_user_from_request(request):
        apikey = request.headers.environ.get('HTTP_X_API_KEY', None)
        if apikey:
            user = user_datastore.find_user(apikey=apikey)
            if not user:
                return None
        else:
            auth = request.headers.get('Authorization')
            if not auth or auth.count(':') != 1:
                return None
            login, password = auth.split(':')
            user = user_datastore.find_user(email=login.strip())
            if user is None:
                return None
            if not verify_and_update_password(password.strip(), user):
                return None
        return user if login_user(user) else None
    security = Security()
    security.init_app(app, user_datastore, login_form=LoginForm)
    app.login_manager.request_loader(load_user_from_request)
    app.login_manager.user_loader(load_user)
    user_logged_out.connect(invalidate_user)
