# -*- coding: utf-8 -*-
from flask.ext.security import  SQLAlchemyUserDatastore

class CacheUserDatastore(SQLAlchemyUserDatastore):

    def __init__(self, db = None, user_model=None, cached_user_model=None,
            role_model=None):
        self.init_app(db, user_model, cached_user_model, role_model)

    def init_app(self, db, user_model, cached_user_model, role_model):
        self.user_model = user_model
        self.role_model = role_model
        self.db = db
        self.cached_user_model = cached_user_model

    def get_user(self, identifier):
        try:
           filter_ = {"id": int(identifier)}
        except ValueError:
           filter_ = {"email": identifier}
        return self.find_user(**filter_)

    def find_user(self, **kwargs):
        if kwargs.keys()[0] == 'id':
            return self.user_model.query.get(kwargs['id'])
        elif kwargs.keys()[0] == 'apikey':
            return self.cached_user_model.get(**kwargs)
        try:
            return self.user_model.query.filter_by(**kwargs).first()
        except StopIteration:
            return None

    def find_role(self, role):
        try:
            return self.role_model.query.filter_by(name=role).first()
        except StopIteration:
            return None
