# -*- coding: utf-8 -*-
from . import db
from .taxis import Taxi as TaxiModel
from flask.ext.security import login_required, roles_accepted,\
        roles_accepted
from datetime import datetime, timedelta
from flask.ext.restplus import abort
from ..utils import HistoryMixin, AsDictMixin, fields
from .security import User
from ..descriptors.common import coordinates_descriptor
from ..api import api
from .. import redis_store

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
    status = db.Column(db.Enum(*status_enum_list,
        name='hail_status'), default='emitted', nullable=False)
    last_status_change = db.Column(db.DateTime)
    db.ForeignKeyConstraint(['operateur_id', 'customer_id'],
        ['customer.operateur_id', 'customer.id'],
        )
    taxi_phone_number = db.Column(db.String, nullable=True)

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

    @login_required
    @roles_accepted('moteur', 'admin')
    def received(self):
        self.status = 'received'
        self.status_changed()
        return True

    def sent_to_operator(self):
        self.status_required('received')
        self.status = 'sent_to_operator'
        self.status_changed()
        return True

    def received_by_operator(self):
        self.status_required('sent_to_operator')
        self.status = 'received_by_operator'
        self.status_changed()
        return True

    def status_required(self, status_required):
        if self.status != status_required:
            abort(400, message="Bad status")
        return True

    @login_required
    @roles_accepted('operateur', 'admin')
    def received_by_taxi(self):
        self.status_required('received_by_operator')
        self.status = 'received_by_taxi'
        self.status_changed()
        return True

    @login_required
    @roles_accepted('operateur', 'admin')
    def accepted_by_taxi(self):
        self.status_required('received_by_taxi')
        if not self.check_time_out(30, 'timeout_taxi'):
            return False
        self.status = 'accepted_by_taxi'
        self.status_changed()
        return True

    @login_required
    @roles_accepted('operateur', 'admin')
    def declined_by_taxi(self):
        self.status_required('received_by_taxi')
        self.status = 'declined_by_taxi'
        self.status_changed()
        return True

    @login_required
    @roles_accepted('operateur', 'admin')
    def incident_taxi(self):
        self.status = 'incident_taxi'
        self.status_changed()
        return True

    @login_required
    @roles_accepted('moteur', 'admin')
    def incident_customer(self):
        self.status = 'incident_customer'
        self.status_changed()
        return True

    @login_required
    @roles_accepted('moteur', 'admin')
    def accepted_by_customer(self):
        self.status_required('accepted_by_taxi')
        if not self.check_time_out(20, 'timeout_customer'):
            return False
        self.status = 'accepted_by_customer'
        self.status_changed()
        return True

    @login_required
    @roles_accepted('moteur', 'admin')
    def declined_by_customer(self):
        self.status_required('accepted_by_taxi')
        self.status = 'declined_by_customer'
        self.status_changed()
        return True

    @login_required
    @roles_accepted('moteur', 'admin')
    def timeout_customer(self):
        self.status_required('accepted_by_taxi')
        self.status = 'timeout_customer'
        self.status_changed()
        return True

    @login_required
    def failure(self):
        self.status = 'failure'
        self.status_changed()

    def check_time_out(self, duration, timeout_status):
        if datetime.now() < (self.last_status_change + timedelta(seconds=duration)):
            return True
        self.status = timeout_status
        return False


    def to_dict(self):
        self.check_time_out()
        return self.as_dict()

    @property
    def taxi(self):
        caracs = TaxiModel.retrieve_caracs(self.taxi_id, redis_store, 0,
                self.operateur.email)
        for operator, carac in caracs:
            if operator != self.operateur.email:
                continue
            return {
                    'position': {'lon': carac['lon'],
                                 'lat' : carac['lat']
                                 },
                    'last_update' : carac['timestamp']
                    }
        return {}

