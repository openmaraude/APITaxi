# -*- coding: utf8 -*-
from backoffice_operateurs.models import db
from sqlalchemy_defaults import Column

class Departement(db.Model):
    id = Column(db.Integer, primary_key=True)
    nom = Column(db.String(255), label='Nom')
    numero = Column(db.String(3), label='Numero')

    def __str__(self):
        return '%r %r' % (self.numero, self.nom)

class ZUPC(db.Model):
    id = Column(db.Integer, primary_key=True)
    departement_id = Column(db.Integer, db.ForeignKey('departement.id'))
    nom = Column(db.String(255), label='Nom')
    shape = Column(db.String(10000), label='Geojson shape')
    departement = db.relationship('Departement',
            backref=db.backref('departements', lazy='dynamic'))

    def __repr__(self):
        return '<ZUPC %r>' % str(self.id)

    def __str__(self):
        return self.__repr__()
