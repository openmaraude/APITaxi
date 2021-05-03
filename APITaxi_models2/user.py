from sqlalchemy import Column

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
    hail_endpoint_production = Column(db.String, server_default='', nullable=False)
    phone_number_customer = Column(db.String)
    phone_number_technical = Column(db.String)
    operator_api_key = Column(db.String)
    operator_header_name = Column(db.String)
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    roles = db.relationship(Role, secondary=RolesUsers.__table__, lazy='joined', viewonly=True)

    # Manager of this User
    manager = db.relationship('User', remote_side=[id], lazy='raise')

    # List of User managed by this User
    managed = db.relationship('User', lazy='raise', viewonly=True)
