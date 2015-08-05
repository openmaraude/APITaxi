# -*- coding: utf-8 -*-
from flask.ext.security import  SQLAlchemyUserDatastore
from .. import region_users, db
from __builtin__ import isinstance
from flask import current_app
from ..models.security import User, Role
from .caching_query import FromCache, RelationshipCache
from sqlalchemy.orm import joinedload

@region_users.cache_on_arguments()
def get_user(identifier):
    try:
       filter_ = {"id": int(identifier)}
    except ValueError:
       filter_ = {"email": identifier}
    return find_user(**filter_)

@region_users.cache_on_arguments()
def find_user(**kwargs):
    session = db.create_scoped_session()
    u = session.query(User).\
            options(joinedload(User.roles)).filter_by(**kwargs).first()
    session.close()
    return u

class CacheUserDatastore(SQLAlchemyUserDatastore):
    def invalidate_user(self, user):
        get_user.invalidate(user.id)
        get_user.invalidate(unicode(user.id))
        get_user.invalidate(user.email)
        find_user.invalidate(id=user.id)
        find_user.invalidate(email=user.email)
        find_user.invalidate(apikey=user.apikey)

    def get_user(self, identifier):
        return get_user(identifier)

    def find_user(self, **kwargs):
        return find_user(**kwargs)


    @region_users.cache_on_arguments()
    def find_role(self, role):
        session = db.create_scoped_session()
        r = session.query(Role).\
                options(FromCache("region_users")).filter_by(name=role).first()
        session.close()
        return r

