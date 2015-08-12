# -*- coding: utf-8 -*-
from flask import g
from .. import db


class ScopedSession(object):
    def __enter__(self):
        self.session = g.get('session', None)
        self.close_session = False
        if not self.session:
            self.session = db.create_scoped_session()
            self.close_session = True
        return self

    def query(self, *args):
        return self.session.query(*args)

    def __exit__(self, type, value, traceback):
        if self.close_session:
            self.session.close()

