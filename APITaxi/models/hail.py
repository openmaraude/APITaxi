# -*- coding: utf-8 -*-
from .taxis import Taxi as TaxiM
from flask.ext.security import login_required, roles_accepted,\
        roles_accepted, current_user
from datetime import datetime, timedelta
from ..utils import HistoryMixin, AsDictMixin, fields
from ..utils.scoped_session import ScopedSession
from .security import User
from ..descriptors.common import coordinates_descriptor
from ..api import api
from ..extensions import redis_store, region_hails, db
from flask_principal import RoleNeed, Permission
from sqlalchemy.orm import validates, joinedload
from flask import g

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


rating_ride_reason_enum = ['late', 'no_credit_card', 'bad_itinerary', 'dirty_taxi']
reporting_customer_reason_enum = ['late', 'aggressive', 'no_show']
incident_customer_reason_enum = ['mud_river', 'parade', 'earthquake']
incident_taxi_reason_enum = ['traffic_jam', 'garbage_truck']
class Hail(db.Model, AsDictMixin, HistoryMixin):
    id = db.Column(db.Integer, primary_key=True)
    creation_datetime = db.Column(db.DateTime, nullable=False)
    operateur_id = db.Column(db.Integer, db.ForeignKey('user.id'),
            nullable=True)
    operateur = db.relationship('User', backref='user_operateur',
        primaryjoin=(operateur_id==User.id), lazy='joined')
    customer_id = db.Column(db.String,
                            nullable=False)
    customer_lon = db.Column(db.Float, nullable=False)
    customer_lat = db.Column(db.Float, nullable=False)
    customer_address = db.Column(db.String, nullable=False)
    customer_phone_number = db.Column(db.String, nullable=False)
    taxi_id = db.Column(db.String, db.ForeignKey('taxi.id'), nullable=False)
    taxi_relation = db.relationship('Taxi', backref="taxi", lazy="joined")
    __status = db.Column(db.Enum(*status_enum_list,
        name='hail_status'), default='emitted', nullable=False, name='status')
    last_status_change = db.Column(db.DateTime)
    db.ForeignKeyConstraint(['operateur_id', 'customer_id'],
        ['customer.operateur_id', 'customer.id'],
        )
    taxi_phone_number = db.Column(db.String, nullable=True)
    rating_ride = db.Column(db.Integer)
    rating_ride_reason = db.Column(db.Enum(*rating_ride_reason_enum,
      name='reason_ride_enum'), nullable=True)
    incident_customer_reason = db.Column(db.Enum(*incident_customer_reason_enum,
        name='incident_customer_reason_enum'), nullable=True)
    incident_taxi_reason = db.Column(db.Enum(*incident_taxi_reason_enum,
        name='incident_taxi_reason_enum'), nullable=True)
# Reporting of the customer by the taxi
    reporting_customer = db.Column(db.Boolean, nullable=True)
    reporting_customer_reason = db.Column(db.Enum(*reporting_customer_reason_enum,
        name='reporting_customer_reason_enum'), nullable=True)


    @validates('rating_ride_reason')
    def validate_rating_ride_reason(self, key, value):
#We need to restrict this to a subset of statuses
        assert value is None or value in rating_ride_reason_enum,\
            'Bad rating_ride_reason\'s value. It can be: {}'.format(
                    rating_ride_reason_enum)
        if current_user.id != self.added_by:
            raise RuntimeError()
        return value

    @validates('incident_customer_reason')
    def validate_incident_customer_reason(self, key, value):
        assert self.status == 'incident_customer', 'Bad status'
        assert value is None or value in incident_customer_reason_enum,\
            'Bad rating_ride_reason\'s value. It can be: {}'.format(
                    incident_customer_reason_enum)
        if current_user.id != self.added_by:
            raise RuntimeError()
        return value

    @validates('incident_taxi_reason')
    def validate_incident_taxi_reason(self, key, value):
        assert self.status == 'incident_taxi', 'Bad status'
        assert value is None or value in incident_taxi_reason_enum,\
            'Bad rating_ride_reason\'s value. It can be: {}'.format(
                    incident_taxi_reason_enum)
        if current_user.id != self.operateur_id:
            raise RuntimeError()
        return value

    @validates('reporting_customer_reason')
    def validate_reporting_customer_reason(self, key, value):
        assert value is None or value in reporting_customer_reason_enum,\
            'Bad reporting_customer_reason\'s value. It can be: {}'.format(
                    reporting_customer_reason_enum)
        if current_user.id != self.operateur_id:
            raise RuntimeError()
        return value

    @validates('reporting_customer')
    def validate_reporting_customer(self, key, value):
        if current_user.id != self.operateur_id:
            raise RuntimeError()
        return value

    @validates('rating_ride')
    def validate_rating_taxi(self, key, value):
#We need to restrict this to a subset of statuses
        assert 1 <= value <= 5, 'Rating value has to be 1 <= value <= 5'
        return value

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
        if value == self.__status:
            return True
        roles_accepted = self.roles_accepted.get(value, None)
        if roles_accepted:
            perm = Permission(*[RoleNeed(role) for role in roles_accepted])
            if not perm.can():
                raise RuntimeError("You're not authorized to set this status")
        status_required = self.status_required.get(value, None)
        if status_required and self.__status != status_required:
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

    def _HailMixin__status_set_no_check(self, value):
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

    @classmethod
    @region_hails.cache_on_arguments(expiration_time=3600*2, namespace='H')
    def get(cls, id_):
        with ScopedSession() as session:
            h = session.query(Hail).options(joinedload(Hail.operateur)).\
                filter_by(id=id_).first()
        return h
