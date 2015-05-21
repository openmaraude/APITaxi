from ..models import db, Vehicle
from ..models.administrative import Departement
# -*- coding: utf-8 -*-
from sqlalchemy_defaults import Column
from sqlalchemy.types import Enum
from ..utils import AsDictMixin, HistoryMixin
from uuid import uuid4
from itertools import compress
from parse import parse

class ADS(db.Model, AsDictMixin, HistoryMixin):
    def __init__(self):
        db.Model.__init__(self)
        HistoryMixin.__init__(self)

    public_fields = set(['numero', 'insee'])
    id = Column(db.Integer, primary_key=True)
    numero = Column(db.String, label=u'Numéro',
            description=u'Numéro de l\'ADS')
    doublage = Column(db.Boolean, label=u'Doublage', default=False,
            nullable=True, description=u'L\'ADS est elle doublée ?')
    insee = Column(db.String, label=u'Code INSEE de la commune d\'attribution',
                   description=u'Code INSEE de la commune d\'attribution')
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)
    vehicle = db.relationship('Vehicle', backref='vehicle')
    owner_type = Column(Enum('company', 'individual', name='owner_type_enum'),
            label=u'Type Propriétaire')
    owner_name = Column(db.String, label=u'Nom du propriétaire')
    category = Column(db.String, label=u'Catégorie de l\'ADS')

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
    departement = db.relationship('Departement', backref='vehicle')

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
    vehicle = db.relationship('Vehicle', backref='vehicle_taxi')
    ads_id = db.Column(db.Integer, db.ForeignKey('ADS.id'), nullable=True)
    ads = db.relationship('ADS', backref='ads')
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'),
            nullable=True)
    driver = db.relationship('Driver', backref='driver')
    status = Column(Enum('free', 'answering', 'occupied', 'oncoming', 'off',
        name='status_taxi_enum'), label='Status', nullable=True, default='free')

    _FORMAT_OPERATOR = "{timestamp} {lat} {lon} {status} {device} {version}"

    def __init__(self, *args, **kwargs):
        kwargs['id'] = str(uuid4())
        HistoryMixin.__init__(self)
        super(self.__class__, self).__init__(**kwargs)

    def operator(self, redis_store):
        #Returns operator, timestamp
        _, scan = redis_store.hscan("taxi:{}".format(self.id))
        if len(scan) == 0:
            return (None, None)
        min_ = (None, None)
        for k, v in scan.iteritems():
             p = parse(self.__class__._FORMAT_OPERATOR, v)
             if p and (not min_[1] or p['timestamp'] < min_[1]):
                min_ = (k, p['timestamp'])
        return min_

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
