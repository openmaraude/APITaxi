# -*- coding: utf8 -*-
from backoffice_operateurs.models import db
from sqlalchemy_defaults import Column

class Departement(db.Model):
    id = Column(db.Integer, primary_key=True)
    nom = Column(db.String(255), label='Nom')
    numero = Column(db.String(3), label='Numéro')

class ZUPC(db.Model):
    id = Column(db.Integer, primary_key=True)
    departement_id = db.Column(db.Integer, db.ForeignKey('departement.id'))
    nom = Column(db.String(255), label='Nom')
    shape = Column(db.String(10000), label='Geojson shape')
