# -*- coding: utf-8 -*-
from . import db
from sqlalchemy_defaults import Column
from APITaxi_utils.mixins import MarshalMixin, FilterOr404Mixin
from APITaxi_utils.caching import CacheableMixin, query_callable
from geoalchemy2 import Geography
from geoalchemy2.shape import to_shape
from shapely.prepared import prep

class Departement(db.Model, MarshalMixin, FilterOr404Mixin):
    id = Column(db.Integer, primary_key=True)
    nom = Column(db.String(255), label='Nom')
    numero = Column(db.String(3), label='Numero')

    def __str__(self):
        return '%s' % (self.numero)

class ZUPC(db.Model, MarshalMixin, CacheableMixin):
    cache_label = 'zupc'
    query_class = query_callable()

    id = Column(db.Integer, primary_key=True)
    departement_id = Column(db.Integer, db.ForeignKey('departement.id'))
    nom = Column(db.String(255), label='Nom')
    insee = Column(db.String(), nullable=True)
    shape = Column(Geography(geometry_type='MULTIPOLYGON', srid=4326,
        spatial_index=False), label='Geography of the shape')
    departement = db.relationship('Departement',
            backref=db.backref('departements'), lazy='joined')
    parent_id = Column(db.Integer, db.ForeignKey('ZUPC.id'))
    parent = db.relationship('ZUPC', remote_side=[id], lazy='joined')
    active = Column(db.Boolean, default=False)
    __geom = None
    __preped_geom = None
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
    def preped_geom(self):
        if self.__preped_geom is None:
            self.__preped_geom = prep(self.geom)
        return self.__preped_geom

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
