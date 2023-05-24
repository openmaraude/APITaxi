from sqlalchemy import Column
from sqlalchemy.orm import synonym

from flask_security import UserMixin, RoleMixin

from . import db, mixins


class RolesUsers(db.Model):
    __table_args__ = (
        db.UniqueConstraint('user_id', 'role_id', name='unique_roles'),
    )

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), primary_key=True)

    user = db.relationship('User', overlaps='roles')
    role = db.relationship('Role', overlaps='roles')


class Role(db.Model, RoleMixin):

    def __repr__(self):
        return '<Role %s (%s)>' % (self.id, self.name)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255), server_default='', nullable=False)


class User(db.Model, UserMixin, mixins.HistoryMixin):

    def __repr__(self):
        return '<User %s (%s - %s)>' % (
            self.id,
            self.email,
            self.commercial_name
        )

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean)
    confirmed_at = db.Column(db.DateTime)
    apikey = db.Column(db.String(36), nullable=False)
    commercial_name = Column(db.String, server_default='', nullable=False)
    email_customer = Column(db.String, server_default='', nullable=False)
    email_technical = Column(db.String, server_default='', nullable=False)
    hail_endpoint_production = Column(db.String, server_default='', nullable=False)
    phone_number_customer = Column(db.String, server_default='', nullable=False)
    phone_number_technical = Column(db.String, server_default='', nullable=False)
    # Should be named operator_header_value
    operator_api_key = Column(db.String, server_default='', nullable=False)
    operator_header_name = Column(db.String, server_default='', nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    fleet_size = db.Column(db.Integer)

    roles = db.relationship(Role, secondary=RolesUsers.__table__, lazy='joined')

    # Manager of this User
    manager = db.relationship('User', remote_side=[id], lazy='raise')

    # List of User managed by this User
    managed = db.relationship('User', lazy='raise', viewonly=True)

    # Required by Flask-Security 4+
    fs_uniquifier = synonym('apikey')
