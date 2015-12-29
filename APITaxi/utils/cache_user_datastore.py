# -*- coding: utf-8 -*-
from flask.ext.security import  SQLAlchemyUserDatastore
from ..extensions import db, regions
from flask import current_app
from ..models.security import User, Role, UserMixin
from sqlalchemy.orm import joinedload, scoped_session
from flask import g, current_app
from sqlalchemy import inspect

class CachedValue(object):
    def __init__(self, v):
        for i in inspect(v).attrs:
            if isinstance(i.value, list):
                setattr(self, i.key, [])
                for i2 in i.value:
                    getattr(self, i.key).append(CachedValue(i2))
            else:
                setattr(self, i.key, i.value)

    @classmethod
    def create(cls, **kwargs):
        def creator():
            v = cls.base_class.query.filter_by(**kwargs).first()
            if v:
                return cls(v)
            return None
        return creator

    @classmethod
    def get_key(cls, **kwargs):
        return '{}.{}[{}]'.format(cls.base_class.__tablename__,
                kwargs.keys()[0], kwargs.values()[0])

    @classmethod
    def get(cls, **kwargs):
        return regions[cls.base_class.cache_label].get_or_create(
                cls.get_key(**kwargs),
                cls.create(**kwargs)
        )


class CachedUser(CachedValue, UserMixin):
    base_class = User


class CacheUserDatastore(SQLAlchemyUserDatastore):

    def __init__(self, db = None, user_model=None, role_model=None):
        self.user_model = user_model
        self.role_model = role_model
        self.db = db

    def init_app(self, db, user_model, role_model):
        self.user_model = user_model
        self.role_model = role_model
        self.db = db

    def get_user(self, identifier):
        try:
           filter_ = {"id": int(identifier)}
        except ValueError:
           filter_ = {"email": identifier}
        return self.find_user(**filter_)

    def find_user(self, **kwargs):
        if kwargs.keys()[0] == 'id':
            return User.query.get(kwargs['id'])
        elif kwargs.keys()[0] == 'apikey':
            return CachedUser.get(**kwargs)
        try:
            return User.query.filter_by(**kwargs).first()
        except StopIteration:
            return None

    def find_role(self, role):
        try:
            return Role.query.filter_by(name=role).first()
        except StopIteration:
            return None
