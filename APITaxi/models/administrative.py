# -*- coding: utf-8 -*-
from ..models import db
from sqlalchemy_defaults import Column
from ..utils import MarshalMixin
import geojson, shapely
from operator import itemgetter

class Departement(db.Model, MarshalMixin):
    id = Column(db.Integer, primary_key=True)
    nom = Column(db.String(255), label='Nom')
    numero = Column(db.String(3), label='Numero')

    def __str__(self):
        return '%r %r' % (self.numero, self.nom)

class ZUPC(db.Model, MarshalMixin):
    id = Column(db.Integer, primary_key=True)
    departement_id = Column(db.Integer, db.ForeignKey('departement.id'))
    nom = Column(db.String(255), label='Nom')
    insee = Column(db.String(), nullable=True)
    shape = Column(db.LargeBinary(), label='Geojson shape')
    departement = db.relationship('Departement',
            backref=db.backref('departements', lazy='dynamic'))
    parent_id = Column(db.Integer, db.ForeignKey('ZUPC.id'))
    parent = db.relationship('ZUPC', remote_side=[id])
    __geom = None
    __left = __right = __bottom = __top = None

    @property
    def geom(self):
        if not self.__geom:
            self.__geom = self.shape
        return self.__geom

    @geom.setter
    def geom(self, value):
        self.__geom = shapely.shape(geojson.loads(value))

    @property
    def left(self):
        if not self.__left:
            self.__left = min(self.__geom.coordinates, key=itemgetter(0))
        return self.__left

    @property
    def right(self):
        if not self.__right:
            self.__right = max(self.__geom.coordinates, key=itemgetter(0))
        return self.__right

    @property
    def bottom(self):
        if not self.__bottom:
            self.__bottom = min(self.__geom.coordinates, key=itemgetter(1))
        return self.__bottom

    @property
    def top(self):
        if not self.__top:
            self.__top = max(self.__geom.coordinates, key=itemgetter(1))
        return self.__top

    def __repr__(self):
        return '<ZUPC %r>' % str(self.id)

    def __str__(self):
        return self.nom
