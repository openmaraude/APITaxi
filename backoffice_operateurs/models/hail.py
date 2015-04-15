# -*- coding: utf8 -*-
from . import db
from flask.ext.security import login_required, roles_accepted,\
        roles_required
from datetime import datetime
from flask import abort

status_enum_list = [ 'emitted', 'received',
    'sent_to_operator', 'received_by_operator',
    'received_by_taxi', 'accepted_by_taxi',
    'declined_by_taxi', 'incident_client',
    'incident_taxi', 'timeout_client', 'timeout_taxi',
        'outdated_client', 'outdated_taxi']#This may be redundant
class Hail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creation_datetime = db.Column(db.DateTime, nullable=False)
    client_id = db.Column(db.Integer, nullable=False)
    client_lon = db.Column(db.Float, nullable=False)
    client_lat = db.Column(db.Float, nullable=False)
    taxi_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum(*status_enum_list,
        name='hail_status'), default='emitted', nullable=False)
    last_status_change = db.Column(db.DateTime)

    def status_changed(self):
        self.last_status_change = datetime.now().isoformat()

    def check_last_status(self, status_required):
        if self.status != status_required:
            abort(500)


    @login_required
    @roles_required('moteur')
    def received(self):
        self.status = 'received'
        self.status_changed()

    def sent_to_operator(self):
        self.status_required('received')
        self.status = 'sent_to_operator'
        self.status_changed()

    def received_by_operator(self):
        self.status_required('sent_to_operator')
        self.status = 'received_by_operator'
        self.status_changed()

    @login_required
    @roles_required('operateur')
    def received_by_taxi(self):
        self.status_required('received_by_operator')
        self.status = 'received_by_taxi'
        self.status_changed()

    @login_required
    @roles_required('operateur')
    def accepted_by_taxi(self):
        self.status_required('received_by_taxi')
        self.status = 'accepted_by_taxi'
        self.status_changed()

    @login_required
    @roles_required('operateur')
    def declined_by_taxi(self):
        self.status_required('received_by_taxi')
        self.status = 'declined_by_taxi'
        self.status_changed()

    @login_required
    @roles_required('operateur')
    def incident_taxi(self):
        self.status = 'incident_taxi'
        self.status_changed()

    @login_required
    @roles_required('moteur')
    def incident_client(self):
        self.status = 'incident_client'
        self.status_changed()

    def check_time_out(self):
        pass

    def to_dict(self):
        self.check_time_out()
        return {
            "id": self.id,
            "creation_datetime": self.creation_datetime,
            "client_id": self.client_id,
            "client_lon": self.client_lon,
            "client_lat": self.client_lat,
            "taxi_id": self.taxi_id,
            "status": self.status,
            "last_status_change": self.last_status_change
            }
