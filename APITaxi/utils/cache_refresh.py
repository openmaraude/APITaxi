from sqlalchemy import event
from threading import Thread, current_thread
from ..extensions import db, region_hails, user_datastore
from sqlalchemy.orm import joinedload
from flask.ext.login import current_user
from flask import current_app, copy_current_request_context, g

def cache_refresh(session, refresher, *args, **kwargs):
    @event.listens_for(session, "after_commit")
    def do_refresh(session):
        @copy_current_request_context
        def execute_function(refreshers):
            s = db.create_scoped_session()
            setattr(g, 'session', s())
            for refresher in refreshers:
                kwargs = refresher.get('kwargs', {})
                args = refresher.get('args', [])
                refresher['func'](*args, **kwargs)
            s.close()
        t = Thread(target=execute_function, args=[refresher])
        t.daemon = True
        t.start()

def invalidate_user(sender, user, **extra):
    cache_refresh(db.session(), refresh_user, current_user.id, thread=True)

def refresh_user(user_id, thread=False):
    user = user_datastore.find_user.refresh(user_datastore, id=user_id)
    user_datastore.get_user.set(user, user.id)
    user_datastore.get_user.set(user, unicode(user.id))
    user_datastore.get_user.set(user, user.email)
    user_datastore.find_user.set(user, email=user.email)
    user_datastore.find_user.set(user, apikey=user.apikey)
