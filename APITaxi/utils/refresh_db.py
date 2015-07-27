# -*- coding: utf-8 -*-
#Source: http://dogpilecache.readthedocs.org/en/latest/usage.html

from sqlalchemy import event
from sqlalchemy.orm import Session

def cache_refresh(session, refresher, *args, **kwargs):
    """
    Refresh the functions cache data in a new thread. Starts refreshing only
    after the session was committed so all database data is available.
    """
    assert isinstance(session, Session), \
        "Need a session, not a sessionmaker or scoped_session"

    @event.listens_for(session, "after_commit")
    def do_refresh(session):
        t = Thread(target=refresher, args=args, kwargs=kwargs)
        t.daemon = True
        t.start()
