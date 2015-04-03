from flask.ext.login import current_user
from datetime import datetime
from flask import request
from sqlalchemy_defaults import Column
from sqlalchemy.types import Integer, DateTime, Enum, String
from sqlalchemy.schema import ForeignKey
from sqlalchemy.ext.declarative import declared_attr


class AsDictMixin:
    def as_dict(self):
       return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class HistoryMixin:

    @declared_attr
    def added_by(self):
        return Column(Integer, ForeignKey('user.id'))

    added_at = Column(DateTime)
    added_via = Column(Enum('form', 'api', name="sources"))
    source = Column(String(255), default='added_by')
    last_update_at = Column(DateTime, nullable=True)

    to_exclude = ['added_at', 'added_via', 'source', 'last_update_at']

    def __init__(self):
        self.added_by = current_user.id if current_user else None
        self.added_at = datetime.now().isoformat()
        self.added_via = 'form' if 'form' in request.url_rule else 'api'
        self.source = 'added_by'
