# -*- coding: utf-8 -*-
from flask.ext.security import  SQLAlchemyUserDatastore
from .. import region_users, db
from __builtin__ import isinstance
from flask import current_app
from ..models.security import User, Role
from .caching_query import FromCache, RelationshipCache
from sqlalchemy.orm import joinedload

class CacheUserDatastore(SQLAlchemyUserDatastore):
    def invalidate_user(self, user):
        self.get_user.invalidate(user.id)
        self.get_user.invalidate(user.email)
        self.find_user.invalidate(id=user.id)
        self.find_user.invalidate(email=user.email)
        self.find_user.invalidate(apikey=user.apikey)

    @region_users.cache_on_arguments()
    def get_user(self, identifier):
        try:
           filter_ = {"id": int(identifier)}
        except ValueError:
           filter_ = {"email": identifier}
        return self.find_user(**filter_)

    @region_users.cache_on_arguments()
    def find_user(self, **kwargs):
        session = db.create_scoped_session()
        u = session.query(User).\
                options(joinedload(User.roles)).filter_by(**kwargs).first()
        session.close()
        return u

    @region_users.cache_on_arguments()
    def find_role(self, role):
        session = db.create_scoped_session()
        r = session.query(Role).\
                options(FromCache("region_users")).filter_by(name=role).first()
        session.close()
        return r

