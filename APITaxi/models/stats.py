#coding: utf-8
from ..extensions import db

class ActiveTaxis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    zupc_id = db.Column(db.Integer, index=True)
    operator_id = db.Column(db.Integer, index=True)
    timestamp = db.Column(db.DateTime)
    nb_taxis = db.Column(db.Integer)
