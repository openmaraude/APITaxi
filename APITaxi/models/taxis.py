# -*- coding: utf-8 -*-

from . import db
from .vehicle import Vehicle, VehicleDescription, Model, Constructor
from .administrative import ZUPC, Departement
from .security import User
from APITaxi_utils import fields, get_columns_names
from APITaxi_utils.mixins import (GetOr404Mixin, AsDictMixin, HistoryMixin,
    FilterOr404Mixin)
from APITaxi_utils.caching import CacheableMixin, query_callable, cache_in
from APITaxi_utils.get_short_uuid import get_short_uuid
from sqlalchemy_defaults import Column
from sqlalchemy.types import Enum
from sqlalchemy.orm import validates
from six import string_types
from parse import with_pattern
import time
from flask import g, current_app
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime
from itertools import groupby


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
    def marshall_obj(cls, show_all=False, filter_id=False, level=0, api=None):
        if level >=2:
            return {}
        return_ = super(ADS, cls).marshall_obj(show_all, filter_id,
                level=level+1, api=api)
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


class TaxiRedis(object):
    _caracs = None
    _DISPONIBILITY_DURATION = 15*60 #Used in "is_fresh, is_free'
    _FORMAT_OPERATOR = '{timestamp:Number} {lat} {lon} {status} {device}'
    _fresh_operateurs_timestamps = None


    def __init__(self, id_, caracs=None, caracs_list=None):
        self._caracs = caracs
        self.id = id_
        self._fresh_operateurs_timestamps = None
        if isinstance(caracs, dict):
            self._caracs = self.transform_caracs(caracs)
        if caracs_list:
            self._caracs = {v[0].split(':')[1]: {
                'coords': {'lat': v[1][1][0], 'lon': v[1][1][1]},
                'timestamp': v[1][2], 'distance': v[1][0]}
                    for v in caracs_list
            }
        if self._caracs:
            self._min_caracs = min(self._caracs.values(), key=lambda v: v['timestamp'])
        else:
            self._min_caracs = None

    @property
    def coords(self):
        return (self._min_caracs['coords'] if self._min_caracs else None)

    @property
    def distance(self):
        return (self._min_caracs['distance'] if self._min_caracs else None)

    @property
    def lon(self):
        return self.coords['lon'] if self._min_caracs else None

    @property
    def lat(self):
        return self.coords['lat'] if self._min_caracs else None

    @staticmethod
    def parse_redis(v):
        r = dict()
        r['timestamp'], r['lat'], r['lon'], r['status'], r['device'], r['version'] = v.decode().split(' ')
        r['timestamp'] = parse_number(r['timestamp'])
        return r

    def caracs(self, min_time):
        if self._caracs is None:
            self._caracs = self.__class__.retrieve_caracs(self.id)
        for i in self._caracs.iteritems():
            if i[1]['timestamp'] < min_time:
                continue
            yield i

    def is_fresh(self, operateur=None):
        min_time = int(time.time() - self._DISPONIBILITY_DURATION)
        if operateur:
            v = current_app.extensions['redis'].hget('taxi:{}'.format(self.id), operateur)
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

    @staticmethod
    def transform_caracs(caracs):
        return {k.decode(): TaxiRedis.parse_redis(v) for k, v in caracs.iteritems()}

    @classmethod
    def retrieve_caracs(cls, id_):
        _, scan = current_app.extensions['redis'].hscan("taxi:{}".format(id_))
        if not scan:
            return []
        return cls.transform_caracs(scan)


    def get_operator(self, min_time=None, favorite_operator=None):
        if not min_time:
            min_time = int(time.time() - self._DISPONIBILITY_DURATION)
        min_return = (None, min_time)
        for operator, timestamp in self.get_fresh_operateurs_timestamps():
            if operator == favorite_operator:
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
            self._fresh_operateurs_timestamps = list(map(
                lambda (email, c): (email, c['timestamp']),
                caracs
            ))
        return self._fresh_operateurs_timestamps


    def _is_free(self, descriptions, func_added_by, func_status, min_time=None):
        if not min_time:
            min_time = int(time.time() - self._DISPONIBILITY_DURATION)
        users = map(lambda u_c : u_c[0],
                    self.get_fresh_operateurs_timestamps(min_time))
        return len(users) > 0 and\
                all(map(lambda desc: func_added_by(desc) not in users\
                    or func_status(desc) == 'free',
                    descriptions))


    def set_avaibility(self, operator_email, status):
        taxi_id_operator = "{}:{}".format(self.id, operator_email)
        if status == 'free':
            current_app.extensions['redis'].srem(
                current_app.config['REDIS_NOT_AVAILABLE'], taxi_id_operator)
        else:
            current_app.extensions['redis'].sadd(
                current_app.config['REDIS_NOT_AVAILABLE'], taxi_id_operator)


class Taxi(CacheableMixin, db.Model, HistoryMixin, AsDictMixin, GetOr404Mixin,
        TaxiRedis):
    @declared_attr
    def added_by(cls):
        return Column(db.Integer,db.ForeignKey('user.id'))
    cache_label = 'taxis'
    query_class = query_callable()

    def __init__(self, *args, **kwargs):
        db.Model.__init__(self)
        HistoryMixin.__init__(self)
        kwargs['id'] = kwargs.get('id', None)
        if not kwargs['id']:
            kwargs['id'] = str(get_short_uuid())
        super(self.__class__, self).__init__(**kwargs)
        HistoryMixin.__init__(self)
        TaxiRedis.__init__(self, self.id)

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
        self.last_update_at = datetime.now()


    def is_free(self, min_time=None):
        return self._is_free(self.vehicle.descriptions,
                lambda desc: User.query.get(desc.added_by).email,
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
        RawTaxi.flush(self.id)



class RawTaxi(object):
    region = 'taxis_cache_sql'
    fields_get = {
        "taxi": get_columns_names(Taxi),
        "model": get_columns_names(Model),
        "constructor": get_columns_names(Constructor),
        "vehicle_description": get_columns_names(VehicleDescription),
        "vehicle": get_columns_names(Vehicle),
        '"ADS"': get_columns_names(ADS),
        "driver": get_columns_names(Driver),
        "departement": get_columns_names(Departement),
        "u": ['email']
    }

    request_in = """SELECT {} FROM taxi
LEFT OUTER JOIN vehicle ON vehicle.id = taxi.vehicle_id
LEFT OUTER JOIN vehicle_description ON vehicle.id = vehicle_description.vehicle_id
LEFT OUTER JOIN model ON model.id = vehicle_description.model_id
LEFT OUTER JOIN constructor ON constructor.id = vehicle_description.constructor_id
LEFT OUTER JOIN "ADS" ON "ADS".id = taxi.ads_id
LEFT OUTER JOIN driver ON driver.id = taxi.driver_id
LEFT OUTER JOIN departement ON departement.id = driver.departement_id
LEFT OUTER JOIN "user" AS u ON u.id = vehicle_description.added_by
WHERE taxi.id IN %s ORDER BY taxi.id""".format(", ".join(
    [", ".join(["{0}.{1} AS {2}_{1}".format(k, v2, k.replace('"', '')) for v2 in v])
        for k, v  in fields_get.items()])
    )

    @staticmethod
    def generate_dict(taxi_db, taxi_redis=None, operator=None, min_time=None,
            favorite_operator=None):
        taxi_id = taxi_db[0]['taxi_id']
        if not taxi_db[0]['taxi_ads_id']:
            current_app.logger.debug('Taxi {} has no ADS'.format(taxi_id))
            return None
        if taxi_redis:
            operator, timestamp = taxi_redis.get_operator(min_time, favorite_operator)
            if not operator:
                current_app.logger.debug('Unable to find operator for taxi {}'.format(taxi_id))
                return None
        else:
            timestamp = None
        taxi = None
        for t in taxi_db:
            if t['u_email'] == operator:
                taxi = t
                break
        if not taxi:
            return None
        characs = VehicleDescription.get_characs(
                lambda o, f: o.get('vehicle_description_{}'.format(f)), t)
        return {
            "id": taxi_id,
            "operator": t['u_email'],
            "position": taxi_redis.coords if taxi_redis else None,
            "vehicle": {
                "model": taxi['model_name'],
                "constructor": taxi['constructor_name'],
                "color": taxi['vehicle_description_color'],
                "characteristics": characs,
                "nb_seats": taxi['vehicle_description_nb_seats'],
                "licence_plate": taxi['vehicle_licence_plate'],
            },
            "ads": {
                "insee": taxi['ads_insee'],
                "numero": taxi['ads_numero']
            },
            "driver": {
                "departement": taxi['departement_numero'],
                "professional_licence": taxi['driver_professional_licence']
            },
            "last_update": timestamp,
            "crowfly_distance": float(taxi_redis.distance) if taxi_redis else None,
            "rating": 4.5,
            "status": taxi['vehicle_description_status']
        }


    @staticmethod
    def get(ids=None, operateur_id=None,id_=None):
        return [[v for v in l
                if not operateur_id or v['vehicle_description_added_by'] == operateur_id]
                for l in cache_in(RawTaxi.request_in, ids,
                            RawTaxi.region, get_id=lambda v: v[0]['taxi_id'],
                            transform_result=lambda r: map(lambda v: list(v[1]),
                            groupby(r, lambda t: t['taxi_id']),))
               if l]

    @staticmethod
    def flush(id_):
        current_app.extensions['redis'].delete((RawTaxi.region, id_))

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

