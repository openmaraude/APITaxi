from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID

from flask_security import UserMixin, RoleMixin

from . import db


class RolesUsers(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), primary_key=True)

    user = db.relationship('User')
    role = db.relationship('Role')


class Role(db.Model, RoleMixin):

    def __repr__(self):
        return '<Role %s (%s)>' % (self.id, self.name)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class User(db.Model, UserMixin):

    def __repr__(self):
        return '<User %s (%s - %s)>' % (
            self.id,
            self.email,
            self.commercial_name
        )

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean)
    confirmed_at = db.Column(db.DateTime)
    apikey = db.Column(db.String(36), nullable=False)
    commercial_name = Column(db.String)
    email_customer = Column(db.String)
    email_technical = Column(db.String)
    hail_endpoint_production = Column(db.String)
    hail_endpoint_staging = Column(db.String)
    hail_endpoint_testing = Column(db.String)
    phone_number_customer = Column(db.String)
    phone_number_technical = Column(db.String)
    operator_api_key = Column(db.String)
    operator_header_name = Column(db.String)

    roles = db.relationship(Role, secondary=RolesUsers.__table__, lazy='joined')
    logos = db.relationship('Logo', lazy='raise')


class Logo(db.Model):

    def __repr__(self):
        return '<Logo %s (size %s of user %s)>' % (self.id, self.size, self.user_id)

    id = db.Column(UUID, primary_key=True)
    size = db.Column(db.String)
    format = db.Column('format_', db.String)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    user = db.relationship(User, lazy='raise')
