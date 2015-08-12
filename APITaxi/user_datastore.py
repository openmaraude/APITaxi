# -*- coding: utf-8 -*-
from .utils.cache_user_datastore import CacheUserDatastore
from . import db
from .models import security

user_datastore = CacheUserDatastore(db, security.User,
                            security.Role)
