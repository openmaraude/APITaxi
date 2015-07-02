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
    __left = None
    __right = None
    __top = None
    __bottom = None
    __geom = None

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
    def left(self):
        if self.__left is None:
            self.__left = min([min(geom.exterior.coords, key=itemgetter(0)) for geom in self.geom.geoms])[0]
        return self.__left

    @property
    def right(self):
        if self.__right is None:
            self.__right = max([max(geom.exterior.coords, key=itemgetter(0)) for geom in self.geom.geoms])[0]
        return self.__right


    @property
    def bottom(self):
        if self.__bottom is None:
            self.__bottom = min([min(geom.exterior.coords, key=itemgetter(1)) for geom in self.geom.geoms])[1]
        return self.__bottom

    @property
    def top(self):
        if self.__top is None:
            self.__top = max([max(geom.exterior.coords, key=itemgetter(1)) for geom in self.geom.geoms])[1]
        return self.__top

