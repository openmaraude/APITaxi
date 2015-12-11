# -*- coding: utf-8 -*-
from ..models import vehicle
from ..extensions import (regions, db, user_datastore, redis_store,
        get_short_uuid)
from ..models.vehicle import Vehicle, VehicleDescription
from ..models.administrative import ZUPC
from ..utils import AsDictMixin, HistoryMixin, fields, FilterOr404Mixin
from ..utils.mixins import GetOr404Mixin
from ..utils.caching import CacheableMixin, query_callable
from sqlalchemy_defaults import Column
from sqlalchemy.types import Enum
from sqlalchemy.orm import validates
from six import string_types
from itertools import compress
from parse import parse, with_pattern
import time, operator
from sqlalchemy.orm import joinedload, sessionmaker, scoped_session
from flask import g, current_app
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime


owner_type_enum = ['company', 'individual']
class ADS(HistoryMixin, db.Model, AsDictMixin, FilterOr404Mixin):
    @declared_attr
    def added_by(cls):
        return Column(db.Integer,db.ForeignKey('user.id'))
    def __init__(self, licence_plate=None):
        db.Model.__init__(self)
        HistoryMixin.__init__(self)
        if licence_plate:
            self.vehicle = licence_plate

    public_fields = set(['numero', 'insee'])
    id = Column(db.Integer, primary_key=True)
    numero = Column(db.String, label=u'Numéro',
            description=u'Numéro de l\'ADS')
    doublage = Column(db.Boolean, label=u'Doublage', default=False,
            nullable=True, description=u'L\'ADS est elle doublée ?')
    insee = Column(db.String, label=u'Code INSEE de la commune d\'attribution',
                   description=u'Code INSEE de la commune d\'attribution')
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)
    _vehicle = db.relationship('Vehicle', lazy='joined')
    owner_type = Column(Enum(*owner_type_enum, name='owner_type_enum'),
            label=u'Type Propriétaire')
    owner_name = Column(db.String, label=u'Nom du propriétaire')
    category = Column(db.String, label=u'Catégorie de l\'ADS')
    zupc_id = db.Column(db.Integer, db.ForeignKey('ZUPC.id'), nullable=True)

    @property
    def zupc(self):
        return ZUPC.cache.get(self.zupc_id)

    @validates('owner_type')
    def validate_owner_type(self, key, value):
        assert value in owner_type_enum
        return value

    @classmethod
    def can_be_listed_by(cls, user):
        return super(ADS, cls).can_be_listed_by(user) or user.has_role('prefecture')

    @classmethod
    def marshall_obj(cls, show_all=False, filter_id=False, level=0):
        if level >=2:
            return {}
        return_ = super(ADS, cls).marshall_obj(show_all, filter_id, level=level+1)
        return_['vehicle_id'] = fields.Integer()
        return return_

    @property
    def vehicle(self):
        return vehicle.Vehicle.query.get(self.vehicle_id)

    @vehicle.setter
    def vehicle(self, vehicle):
        if isinstance(vehicle, string_types):
            self.__vehicle = Vehicle(vehicle)
        else:
            self.__vehicle = Vehicle(vehicle.licence_plate)


    def __repr__(self):
        return '<ADS %r>' % unicode(self.id)

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)


class Driver(HistoryMixin, db.Model, AsDictMixin, FilterOr404Mixin):
    @declared_attr
    def added_by(cls):
        return Column(db.Integer,db.ForeignKey('user.id'))
    def __init__(self):
        db.Model.__init__(self)
        HistoryMixin.__init__(self)
    id = Column(db.Integer, primary_key=True)
    last_name = Column(db.String(255), label='Nom', description=u'Nom du conducteur')
    first_name = Column(db.String(255), label=u'Prénom',
            description=u'Prénom du conducteur')
    birth_date = Column(db.Date(),
        label=u'Date de naissance (format année-mois-jour)',
        description=u'Date de naissance (format année-mois-jour)')
    professional_licence = Column(db.String(),
            label=u'Numéro de la carte professionnelle',
            description=u'Numéro de la carte professionnelle')

    departement_id = Column(db.Integer, db.ForeignKey('departement.id'),
            nullable=True)
    departement = db.relationship('Departement', backref='vehicle',
            lazy="joined")


    @classmethod
    def can_be_listed_by(cls, user):
        return super(Driver, cls).can_be_listed_by(user) or user.has_role('prefecture')

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return '<drivers %r>' % unicode(self.id)

@with_pattern(r'\d+(\.\d+)?')
def parse_number(str_):
    return int(float(str_))


class UserPseudoCache(object):
    def __init__(self):
        self.cache = dict()

    def get(self, item):
        if not item in self.cache:
            self.cache[item] = user_datastore.find_user(email=item)
        return self.cache[item]


class TaxiRedis(object):
    _caracs = None
    _DISPONIBILITY_DURATION = 15*60 #Used in "is_fresh, is_free'
    _FORMAT_OPERATOR = '{timestamp:Number} {lat} {lon} {status} {device}'
    _fresh_operateurs_timestamps = None
    _users_cache = UserPseudoCache()


    def __init__(self, id_, users_cache):
        self._caracs = None
        self.id = id_
        self._fresh_operateurs_timestamps = None
        self._users_cache = users_cache

    @classmethod
    def parse_redis(cls, v):
        return parse(cls._FORMAT_OPERATOR, v.decode(), {'Number': parse_number})

    def caracs(self, min_time):
        if self._caracs is None:
            self._caracs = self.__class__.retrieve_caracs(self.id)
        for i in self._caracs:
            if i[1] is None:
                current_app.logger.error('Taxi {} has wrong format in redis'.format(self.id))
                continue
            if i[1]['timestamp'] < min_time:
                continue
            yield i

    def is_fresh(self, operateur=None):
        min_time = int(time.time() - self._DISPONIBILITY_DURATION)
        if operateur:
            v = redis_store.hget('taxi:{}'.format(self.id), operateur)
            if not v:
                return False
            p = self.parse_redis(v)
            return p['timestamp'] > min_time
        else:
            try:
                self.caracs(min_time).next()
            except StopIteration:
                return False
            return True


    @classmethod
    def retrieve_caracs(cls, id_):
        _, scan = redis_store.hscan("taxi:{}".format(id_))
        if len(scan) == 0:
            return []
        scan = [(k.decode(), cls.parse_redis(v)) for k, v in scan.items()]
        return [(k, v) for k, v in scan]


    def get_operator(self, min_time=None, favorite_operator=None):
        if not min_time:
            min_time = int(time.time() - self._DISPONIBILITY_DURATION)
        min_return = (None, min_time)
        for operator, timestamp in self.get_fresh_operateurs_timestamps():
            if operator.email == favorite_operator:
                min_return = (operator, timestamp)
                break
            if int(timestamp) > min_return[1]:
                min_return = (operator, timestamp)
        if min_return[0] is None:
            return (None, None)
        return min_return


    def get_fresh_operateurs_timestamps(self, min_time=None):
        if not min_time:
            min_time = int(time.time() - self._DISPONIBILITY_DURATION)
        caracs = self.caracs(min_time)
        if not self._fresh_operateurs_timestamps:
            get_user = lambda email: self._users_cache.get(email)
            self._fresh_operateurs_timestamps = list(map(
                lambda (email, c): (get_user(email), c['timestamp']),
                caracs
            ))
            self._fresh_operateurs_timestamps = filter(
                    lambda u_c: u_c[0] is not None,
                    self._fresh_operateurs_timestamps)
        return self._fresh_operateurs_timestamps


    def _is_free(self, descriptions, func_added_by, func_status, min_time=None):
        if not min_time:
            min_time = int(time.time() - self._DISPONIBILITY_DURATION)
        users = map(lambda u_c : u_c[0].id, self.get_fresh_operateurs_timestamps(min_time))
        return len(users) > 0 and\
                all(map(lambda desc: func_added_by(desc) not in users\
                    or func_status(desc) == 'free',
                    descriptions))


class Taxi(CacheableMixin, db.Model, HistoryMixin, AsDictMixin, GetOr404Mixin,
        TaxiRedis):
    @declared_attr
    def added_by(cls):
        return Column(db.Integer,db.ForeignKey('user.id'))
    cache_label = 'taxis'
    cache_regions = regions
    query_class = query_callable(regions)

    def __init__(self, *args, **kwargs):
        db.Model.__init__(self)
        HistoryMixin.__init__(self)
        kwargs['id'] = kwargs.get('id', None)
        if not kwargs['id']:
            kwargs['id'] = str(get_short_uuid())
        HistoryMixin.__init__(self)
        super(self.__class__, self).__init__(**kwargs)
        TaxiRedis.__init__(self, self.id, UserPseudoCache())

    id = Column(db.String, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'),
            nullable=True)
    vehicle = db.relationship('Vehicle', backref='vehicle_taxi', lazy='joined')
    ads_id = db.Column(db.Integer, db.ForeignKey('ADS.id'), nullable=True)
    ads = db.relationship('ADS', backref='ads', lazy='joined')
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'),
            nullable=True)
    driver = db.relationship('Driver', backref='driver', lazy='joined')

    _ACTIVITY_TIMEOUT = 15*60 #Used for dash

    @property
    def rating(self):
        return 4.5

    @property
    def status(self):
        return self.vehicle.description.status

    @status.setter
    def status(self, status):
        self.vehicle.description.status = status


    def is_free(self, min_time=None):
        return self._is_free(self.vehicle.descriptions,
                lambda desc: desc.added_by,
                lambda desc: desc.status,
                min_time)

    def set_free(self):
#For debugging purposes
        for desc in self.vehicle.descriptions:
            desc.status = 'free'

    @property
    def driver_professional_licence(self):
        return self.driver.professional_licence

    @property
    def vehicle_licence_plate(self):
        return self.vehicle.licence_plate

    @property
    def ads_numero(self):
        return self.ads.numero

    @property
    def driver_insee(self):
        return self.ads.insee

    @property
    def driver_departement(self):
        return self.driver.departement


    map_hail_status_taxi_status = {'emitted': 'free',
            'received': 'answering',
            'sent_to_operator': 'answering',
            'received_by_operator': 'answering',
            'received_by_taxi': 'answering',
            'accepted_by_taxi': 'answering',
            'accepted_by_customer': 'oncoming',
            'declined_by_taxi': 'free',
            'declined_by_customer': 'free',
            'incident_customer': 'free',
            'incident_taxi': 'free',
            'timeout_customer': 'free',
            'timeout_taxi': 'free',
            'outdated_customer': 'free',
            'outdated_taxi': 'free',
                'failure': 'free'}

    def synchronize_status_with_hail(self, hail):
        description = self.vehicle.get_description(hail.operateur)
        description.status = self.map_hail_status_taxi_status[hail.status]
        self.last_update_at = datetime.now()


def refresh_taxi(**kwargs):
    id_ = kwargs.get('id_', None)
    if id_:
        Taxi.getter_db.refresh(id_)
        return
    filters = []
    for k in ('ads', 'vehicle', 'driver'):
        param = kwargs.get(k, None)
        if not param:
            continue
        filter_k = '{}_id'.format(k)
        if isinstance(param, list):
            filters.extend([{filter_k: i} for i in param])
        elif param:
            filters.extend([{filter_k: param}])
    for filter_ in filters:
        for taxi in Taxi.query.filter_by(**filter_):
            Taxi.getter_db.refresh(Taxi, taxi.id)

