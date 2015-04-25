# -*- coding: utf8 -*-
from flask.ext.login import current_user
from flask import request
from sqlalchemy_defaults import Column
from sqlalchemy.types import Integer, DateTime, Enum, String
from sqlalchemy.schema import ForeignKey
from sqlalchemy.ext.declarative import declared_attr
from flask.ext.restplus import fields
from datetime import datetime
from .fields import Date

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

    @classmethod
    def to_exclude(cls):
        columns = filter(lambda f: isinstance(getattr(HistoryMixin, f), Column), HistoryMixin.__dict__.keys())
        return columns

    def __init__(self):
        self.added_by = current_user.id if current_user else None
        self.added_at = datetime.now().isoformat()
        self.added_via = 'form' if 'form' in request.url_rule.rule else 'api'
        self.source = 'added_by'

    def can_be_deleted_by(self, user):
        return user.has_role("admin") or self.added_by == user.id

    def can_be_edited_by(self, user):
        return user.has_role("admin") or self.added_by == user.id

    @classmethod
    def can_be_listed_by(cls, user):
        return user.has_role("admin") or user.has_role("operateur")

    @classmethod
    def list_fields(cls):
        columns = cls.__table__.columns._data.keys()
        return set([k for k in columns if k not in cls.to_exclude()])


    def showable_fields(self, user):
        cls = self.__class__
        if user.has_role("admin") or self.added_by == user.id:
            return cls.list_fields()
        return cls.public_fields if hasattr(cls, "public_fields") else set()

    @classmethod
    def marshall_obj(cls, show_all=False, filter_id=False):
        if not show_all and hasattr(cls, 'public_fields'):
            fields_cls = cls.public_fields
        else:
            fields_cls = cls.list_fields()
        map_ = {
            "INTEGER": fields.Integer,
            "BOOLEAN": fields.Boolean,
            "DATETIME": fields.DateTime,
            "DATE": Date,
            "FLOAT": fields.Float,
        }
        return_ = {}
        for k in fields_cls:
            if filter_id and k == "id":
                continue
            f = getattr(cls, k, None)
            if not f or not hasattr(f, 'type'):
                continue
            field_type = map_.get(str(f.type), None)
            kwargs = {}
            if not field_type:
                if isinstance(f.type, Enum):
                    kwargs['enum'] = f.type.enums
                    field_type = fields.String
                elif str(f.type).startswith("VARCHAR"):
                    field_type = fields.String
                else:
                    continue
            kwargs['required'] = not f.nullable
            kwargs['description'] = f.description
            return_[k] = field_type(**kwargs)
        return return_

