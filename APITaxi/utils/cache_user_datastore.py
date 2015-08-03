# -*- coding: utf-8 -*-
from flask.ext.security import  SQLAlchemyUserDatastore
from .. import region_users

class CacheUserDatastore(SQLAlchemyUserDatastore):

    def invalidate_user(self, user):
        self.get_user.invalidate(user.id)
        self.get_user.invalidate(user.email)
        self.find_user.invalidate(user.email)
        self.find_user.invalidate(user.apikey)

    @region_users.cache_on_arguments()
    def get_user(self, identifier):
        return SQLAlchemyUserDatastore.get_user(self, identifier)

    @region_users.cache_on_arguments()
    def find_user(self, **kwargs):
        return SQLAlchemyUserDatastore.find_user(self, **kwargs)

    @region_users.cache_on_arguments()
    def find_role(self, role):
        return SQLAlchemyUserDatastore.find_role(self, find_role)
