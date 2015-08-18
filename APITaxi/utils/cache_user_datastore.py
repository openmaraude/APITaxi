# -*- coding: utf-8 -*-
from flask.ext.security import  SQLAlchemyUserDatastore
from ..extensions import region_users, db
from flask import current_app
from ..models.security import User, Role
from sqlalchemy.orm import joinedload, scoped_session
from flask import g, current_app
from .scoped_session import ScopedSession


class CacheUserDatastore(SQLAlchemyUserDatastore):

    @region_users.cache_on_arguments()
    def get_user(self, identifier):
        try:
           filter_ = {"id": int(identifier)}
        except ValueError:
           filter_ = {"email": identifier}
        return self.find_user(**filter_)

    @region_users.cache_on_arguments()
    def find_user(self, **kwargs):
        with ScopedSession() as session:
            u = session.query(User).options(joinedload(User.roles)).\
                    filter_by(**kwargs).first()
        return u

    @region_users.cache_on_arguments()
    def find_role(self, role):
        with ScopedSession() as session:
            r = session.query(Role).filter_by(name=role).first()
        return r
