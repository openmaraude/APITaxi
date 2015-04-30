# -*- coding: utf8 -*-
from ..models import db
from ..models.administrative import Departement
from sqlalchemy_defaults import Column
from sqlalchemy.types import Enum
from ..utils import AsDictMixin, HistoryMixin
from uuid import uuid4
from itertools import compress


class Vehicle(db.Model, AsDictMixin, HistoryMixin):
    def __init__(self):
        db.Model.__init__(self)
        HistoryMixin.__init__(self)
    id = Column(db.Integer, primary_key=True)
    licence_plate = Column(db.String(80), label=u'Immatriculation',
            description=u'Immatriculation du véhicule')
    model = Column(db.String(255), label=u'Modèle', nullable=True,
            description=u'Modèle du véhicule')
    model_year = Column(db.Integer, label=u'Année', nullable=True,
            description=u'Année de mise en production du véhicule')
    engine = Column(db.String(80), label=u'Motorisation', nullable=True,
            description=u'Motorisation du véhicule')
    horse_power = Column(db.Float(), label=u'Puissance', nullable=True,
            description=u'Puissance du véhicule en chevaux fiscaux')
    type_ = Column(Enum('sedan', 'mpv', 'station_wagon', 'normal', name='vehicle_type_enum'), name='type_',
            label='Type', nullable=True)
    relais = Column(db.Boolean, label=u'Relais', default=False, nullable=True,
            description=u'Est-ce un véhicule relais')
    constructor = Column(db.String(255), label=u'Marque', nullable=True,
            description=u'Marque du véhicule')
    horodateur = Column(db.String(255), label=u'Horodateur', nullable=True,
            description=u'Modèle de l\'horodateur')
    taximetre = Column(db.String(255), label=u'Taximètre', nullable=True,
            description=u'Modèle du taximètre')
    date_dernier_ct = Column(db.Date(),
        label=u'Date du dernier CT (format année-mois-jour)',
        description=u'Date du dernier contrôle technique')
    date_validite_ct = Column(db.Date(),
        label=u'Date de la fin de validité du CT (format année-mois-jour)',
        description=u'Date de fin de validité du contrôle technique')
    luxury = Column(db.Boolean, name='luxury', label='Luxe ?', nullable=True)
    credit_card_accepted = Column(db.Boolean, name='credit_card_accepted',
            label=u'Carte bancaire acceptée ?', nullable=True)
    nfc_cc_accepted = Column(db.Boolean, name='nfc_cc_accepted',
            label=u'Paiement sans contact sur carte bancaire accepté ?',
            nullable=True)
    amex_accepted = Column(db.Boolean, name='amex_accepted',
            label=u'AMEX acceptée ?', nullable=True)
    bank_check_accepted = Column(db.Boolean, name='bank_check_accepted',
            label=u'Chèque bancaire accepté ?', nullable=True)
    fresh_drink = Column(db.Boolean, name='fresh_drink',
            label=u'Boisson fraiche ?', nullable=True)
    dvd_player = Column(db.Boolean, name='dvd_player', label='Lecteur DVD ?',
            nullable=True)
    tablet = Column(db.Boolean, name='tablet', label='Tablette ?',
            nullable=True)
    wifi = Column(db.Boolean, name='wifi', label=u'Wifi à bord ?',
            nullable=True)
    baby_seat = Column(db.Boolean, name='baby_seat', label=u'Siège bébé ?',
            nullable=True)
    bike_accepted = Column(db.Boolean, name='bike_accepted',
            label=u'Transport de vélo', nullable=True)
    pet_accepted = Column(db.Boolean, name='pet_accepted',
            label=u'Animaux de compagnie acceptés ?', nullable=True)
    air_con = Column(db.Boolean, name='air_con',
            label=u'Véhicule climatisé', nullable=True)
    electronic_toll = Column(db.Boolean, name='electronic_toll',
            label=u'Véhicule équipé du télépéage', nullable=True)
    gps = Column(db.Boolean, name='gps', label=u'Véhicule équipé d\'un GPS',
            nullable=True)
    cpam_conventionne = Column(db.Boolean, name='cpam_conventionne',
            label=u'Conventionné assurance maladie', nullable=True)
    every_destination = Column(db.Boolean, name='every_destination',
            label=u'Toute destination', nullable=True)
    color = Column(db.String(255), name='color', label='Couleur : ',
            nullable=True)
    special_need_vehicle = Column(db.Boolean, name='special_need_vehicle',
            label=u'Véhicule spécialement aménagé pour PMR ', nullable=True)

    @property
    def characteristics(self):
        fields = ['special_need_vehicle', 'every_destination', 'gps',
            'electronic_toll', 'air_con', 'pet_accepted', 'bike_accepted',
            'baby_seat', 'wifi', 'tablet', 'dvd_player', 'fresh_drink',
            'amex_accepted', 'bank_check_accepted', 'nfc_cc_accepted',
            'credit_card_accepted', 'luxury']
        return list(compress(fields, map(lambda f: getattr(self, f), fields)))

    def __repr__(self):
        return '<Vehicle %r>' % str(self.id)

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)

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

    def __init__(self, *args, **kwargs):
        kwargs['id'] = str(uuid4())
        HistoryMixin.__init__(self)
        super(self.__class__, self).__init__(**kwargs)

    def operator(self, redis_store):
        #Returns operator, timestamp
        a = redis_store.hscan("taxi:{}".format(self.id))
        if len(a[1]) == 0:
            return (None, None)
        operator, value = min(a[1].iteritems(),
             key=lambda (k, v): v.split(" ")[0])
        return operator, value[0]

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
