# -*- coding: utf-8 -*-
from flask.ext.security import  SQLAlchemyUserDatastore
from ..extensions import db
from flask import current_app
from ..models.security import User, Role
from sqlalchemy.orm import joinedload, scoped_session
from flask import g, current_app

class CacheUserDatastore(SQLAlchemyUserDatastore):

    def get_user(self, identifier):
        try:
           filter_ = {"id": int(identifier)}
        except ValueError:
           filter_ = {"email": identifier}
        return self.find_user(**filter_)

    def find_user(self, **kwargs):
        if kwargs.keys()[0] == 'id':
            return User.cache.get(kwargs['id'])
        try:
            return User.cache.filter(**kwargs).next()
        except StopIteration:
            return None

    def find_role(self, role):
        try:
            return Role.cache.filter(name=role).next()
        except StopIteration:
            return None