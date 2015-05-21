# -*- coding: utf-8 -*-
from flask.ext.security import UserMixin, RoleMixin
from ..models import db
from uuid import uuid4


roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))
    apikey = db.Column(db.String(36), nullable=False)
    hail_endpoint = db.Column(db.String, nullable=True)

    def __init__(self, *args, **kwargs):
        kwargs['apikey'] = str(uuid4())
        super(self.__class__, self).__init__(**kwargs)

    def get_user_from_api_key(self, apikey):
        user = self.user_model.query.filter_by(apikey=apikey)
        return user.get() or None
