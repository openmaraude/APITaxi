# -*- coding: utf-8 -*-
from ..models import vehicle
from ..extensions import region_taxi, db, user_datastore
from ..models.vehicle import Vehicle, VehicleDescription
from sqlalchemy_defaults import Column
from sqlalchemy.types import Enum
from sqlalchemy.orm import validates
from ..utils import AsDictMixin, HistoryMixin, fields
from uuid import uuid4
from six import string_types
from itertools import compress
from parse import parse
import time, operator
from sqlalchemy.orm import joinedload

owner_type_enum = ['company', 'individual']
class ADS(db.Model, AsDictMixin, HistoryMixin):
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
    __vehicle = db.relationship('Vehicle', backref='vehicle', lazy='joined')
    owner_type = Column(Enum(*owner_type_enum, name='owner_type_enum'),
            label=u'Type Propriétaire')
    owner_name = Column(db.String, label=u'Nom du propriétaire')
    category = Column(db.String, label=u'Catégorie de l\'ADS')
    zupc_id = db.Column(db.Integer, db.ForeignKey('ZUPC.id'), nullable=True)
    zupc = db.relationship('ZUPC', backref='ZUPC', lazy='joined')

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
        return self.__vehicle

    @vehicle.setter
    def vehicle(self, vehicle):
        if isinstance(vehicle, string_types):
            self.__vehicle = Vehicle(vehicle)
        else:
            self.__vehicle = Vehicle(vehicle.licence_plate)


    def __repr__(self):
        return '<ADS %r>' % str(self.id)

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)


class Driver(db.Model, AsDictMixin, HistoryMixin):
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
        return '<drivers %r>' % str(self.id)

class Taxi(db.Model, AsDictMixin, HistoryMixin):

    def __init__(self):
        db.Model.__init__(self)
        HistoryMixin.__init__(self)

    id = Column(db.String, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'),
            nullable=True)
    vehicle = db.relationship('Vehicle', backref='vehicle_taxi', lazy='joined')
    ads_id = db.Column(db.Integer, db.ForeignKey('ADS.id'), nullable=True)
    ads = db.relationship('ADS', backref='ads', lazy='joined')
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'),
            nullable=True)
    driver = db.relationship('Driver', backref='driver', lazy='joined')

    _FORMAT_OPERATOR = '{timestamp:d} {lat} {lon} {status} {device}'
    _DISPONIBILITY_DURATION = 60*60

    def __init__(self, *args, **kwargs):
        kwargs['id'] = str(uuid4())
        HistoryMixin.__init__(self)
        super(self.__class__, self).__init__(**kwargs)

    @property
    def status(self):
        return self.vehicle.description.status

    @status.setter
    def status(self, status):
        self.vehicle.description.status = status

    @classmethod
    def retrieve_caracs(cls, id_, redis_store, min_time):
        _, scan = redis_store.hscan("taxi:{}".format(id_))
        if len(scan) == 0:
            return []
        scan = [(k.decode(), parse(cls._FORMAT_OPERATOR, v.decode()))\
                for k, v in scan.items()]
        return [(k, v) for k, v in scan\
                if int(v['timestamp']) >= min_time]

    def caracs(self, redis_store, min_time):
        return self.__class__.retrieve_caracs(self.id, redis_store, min_time)

    def is_free(self, redis_store, min_time=None, operateur=None):
        if not min_time:
            min_time = int(time.time() - self._DISPONIBILITY_DURATION)
        caracs = self.caracs(redis_store, min_time)
        users = map(lambda (email, _): user_datastore.find_user(email=email).id,
                caracs)
        return all(map(lambda desc: desc.added_by not in users or desc.status == 'free',
            self.vehicle.descriptions))

    def is_fresh(self, redis_store, operateur):
        v = redis_store.hget('taxi:{}'.format(self.id), operateur)
        if not v:
            return False
        min_time = int(time.time() - self._DISPONIBILITY_DURATION)
        p = parse(self._FORMAT_OPERATOR, v.decode())
        return p['timestamp'] > min_time

    def set_free(self):
#For debugging purposes
        for desc in self.vehicle.descriptions:
            desc.status = 'free'

    def get_operator(self, redis_store, min_time=None,
            favorite_operator=None):
        if not min_time:
            min_time = int(time.time() - self._DISPONIBILITY_DURATION)
        min_return = (None, min_time)
        caracs = self.caracs(redis_store, min_time)
        if caracs:
            for operator_name, carac in caracs:
                if operator_name == favorite_operator:
                    operator = user_datastore.find_user(email=operator_name)
                    return (operator, carac['timestamp'])
                if int(carac['timestamp']) > min_return[1]:
                    min_return = (operator_name, carac['timestamp'])
        if min_return[0] is None:
            return (None, None)
        operator = user_datastore.find_user(email=min_return[0])
        return (operator, min_return[1])

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

@region_taxi.cache_on_arguments(expiration_time=13*3600)
def get_taxi(id_):
    session = db.create_scoped_session()
    t = session.query(Taxi).options(joinedload(Taxi.ads),
                 joinedload(Taxi.driver), joinedload(Taxi.vehicle))\
                        .filter_by(id=id_).first()
    session.close()
    return t

def invalidate_taxi(ads=None, vehicle=None, driver=None, id_=None):
    filters = {}
    if ads:
        filters['ads_id'] = ads
    if vehicle:
        filters['vehicle_id'] = vehicle
    if driver:
        filters['driver_id'] = driver
    if not filters:
        return
    for taxi in Taxi.query.filter_by(**filters):
        get_taxi.invalidate(taxi.id)
