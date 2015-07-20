# -*- coding: utf-8 -*-
from . import db
from .taxis import Taxi as TaxiM
from flask.ext.security import login_required, roles_accepted,\
        roles_accepted
from datetime import datetime, timedelta
from ..utils import HistoryMixin, AsDictMixin, fields
from .security import User
from ..descriptors.common import coordinates_descriptor
from ..api import api
from .. import redis_store
from flask_principal import RoleNeed, Permission
from sqlalchemy.orm import validates

status_enum_list = [ 'emitted', 'received',
    'sent_to_operator', 'received_by_operator',
    'received_by_taxi',
    'accepted_by_taxi', 'accepted_by_customer',
    'declined_by_taxi', 'declined_by_customer',
    'incident_customer', 'incident_taxi',
    'timeout_customer', 'timeout_taxi',
    'outdated_customer', 'outdated_taxi', 'failure']#This may be redundant

class Customer(db.Model, AsDictMixin, HistoryMixin):
    id = db.Column(db.String, primary_key=True)
    operateur_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                             primary_key=True)
    nb_sanctions = db.Column(db.Integer, default=0)

class Hail(db.Model, AsDictMixin, HistoryMixin):
    id = db.Column(db.Integer, primary_key=True)
    creation_datetime = db.Column(db.DateTime, nullable=False)
    operateur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    operateur = db.relationship('User', backref='user_operateur',
        primaryjoin=(operateur_id==User.id))
    customer_id = db.Column(db.String,
                            nullable=False)
    customer_lon = db.Column(db.Float, nullable=False)
    customer_lat = db.Column(db.Float, nullable=False)
    customer_address = db.Column(db.String, nullable=False)
    customer_phone_number = db.Column(db.String, nullable=False)
    taxi_id = db.Column(db.String, nullable=False)
    __status = db.Column(db.Enum(*status_enum_list,
        name='hail_status'), default='emitted', nullable=False, name='status')
    last_status_change = db.Column(db.DateTime)
    db.ForeignKeyConstraint(['operateur_id', 'customer_id'],
        ['customer.operateur_id', 'customer.id'],
        )
    taxi_phone_number = db.Column(db.String, nullable=True)

    def __init__(self):
        db.Model.__init__(self)
        HistoryMixin.__init__(self)

    timeouts = {
            'received_by_taxi': (30, 'timeout_taxi'),
            'accepted_by_taxi': (20, 'timeout_customer')
    }

    roles_accepted = {
            'received': ['moteur', 'admin'],
            'received_by_taxi': ['operateur', 'admin'],
            'accepted_by_taxi': ['operateur', 'admin'],
            'declined_by_taxi': ['operateur', 'admin'],
            'incident_taxi': ['operateur', 'admin'],
            'incident_customer': ['moteur', 'admin'],
            'accepted_by_customer': ['moteur', 'admin'],
            'declined_by_customer': ['moteur', 'admin'],
    }

    status_required = {
            'sent_to_operator': 'received',
            'received_by_operator': 'sent_to_operator',
            'received_by_taxi': 'received_by_operator',
            'accepted_by_taxi': 'received_by_taxi',
            'declined_by_taxi': 'received_by_taxi',
            'accepted_by_customer': 'accepted_by_taxi',
            'declined_by_customer': 'accepted_by_taxi',
    }

    @property
    def status(self):
        time, next_status = self.timeouts.get(self.__status, (None, None))
        if time:
            self.check_time_out(time, next_status)
        return self.__status

    @status.setter
    def status(self, value):
        assert value in status_enum_list
        roles_accepted = self.roles_accepted.get(value, None)
        if roles_accepted:
            perm = Permission(*[RoleNeed(role) for role in roles_accepted])
            if not perm.can():
                raise RuntimeError("You're not authorized to set this status")
        status_required = self.status_required.get(value, None)
        if status_required and self.status != status_required:
            raise ValueError("You cannot set status from {} to {}".format(self.__status, value))
        self.status_changed()
        self.__status = value

    def _TestHailPut__status_set_no_check(self, value):
#Used for testing purposes
        self.__status = value
        self.status_changed()

    def _TestHailGet__status_set_no_check(self, value):
#Used for testing purposes
        self._TestHailPut__status_set_no_check(value)

    @classmethod
    def marshall_obj(cls, show_all=False, filter_id=False, level=0):
        if level >=2:
            return {}
        return_ = super(Hail, cls).marshall_obj(show_all, filter_id, level=level+1)
        return_['operateur'] = fields.String(attribute='operateur.email')
        return_['id'] = fields.String()
        return_['taxi'] = fields.Nested(api.model('hail_taxi',
                {'position': fields.Nested(coordinates_descriptor),
                 'last_update': fields.Integer()}))
        return return_

    def status_changed(self):
        self.last_status_change = datetime.now()

    def check_time_out(self, duration, timeout_status):
        if datetime.now() < (self.last_status_change + timedelta(seconds=duration)):
            return True
        self.status = timeout_status
        db.session.commit()
        return False

    def to_dict(self):
        self.check_time_out()
        return self.as_dict()

    @property
    def taxi(self):
        for operator, carac in TaxiM.retrieve_caracs(self.taxi_id, redis_store, 0):
            if operator == self.operateur.email:
                return {
                        'position': {'lon': carac['lon'],'lat' : carac['lat']},
                        'last_update' : carac['timestamp']
                        }
        return {}

