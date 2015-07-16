# -*- coding: utf-8 -*-
from ..models import db
from sqlalchemy_defaults import Column
from ..utils import MarshalMixin
import geojson, shapely
from operator import itemgetter
from geoalchemy2 import Geography
from geoalchemy2.shape import to_shape

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
    shape = Column(Geography(geometry_type='MULTIPOLYGON', srid=4326,
        spatial_index=False), label='Geography of the shape')
    departement = db.relationship('Departement',
            backref=db.backref('departements', lazy='dynamic'))
    parent_id = Column(db.Integer, db.ForeignKey('ZUPC.id'))
    parent = db.relationship('ZUPC', remote_side=[id])
    __geom = None
    __bounds = None

    def __repr__(self):
        return '<ZUPC %r>' % str(self.id)

    def __str__(self):
        return self.nom

    @property
    def geom(self):
        if self.__geom is None:
            self.__geom = to_shape(self.shape)
        return self.__geom

    @property
    def bounds(self):
        if not self.__bounds:
            self.__bounds = self.geom.bounds
        return self.__bounds

    @property
    def bottom(self):
        return self.bounds[1]

    @property
    def left(self):
        return self.bounds[0]

    @property
    def top(self):
        return self.bounds[3]

    @property
    def right(self):
        return self.bounds[2]
