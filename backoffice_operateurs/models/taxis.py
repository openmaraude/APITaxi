# -*- coding: utf8 -*-
from ..models import db
from sqlalchemy_defaults import Column
from sqlalchemy.types import Enum
from ..utils import AsDictMixin, HistoryMixin


class Vehicle(db.Model, AsDictMixin, HistoryMixin):
    def __init__(self):
        db.Model.__init__(self)
        HistoryMixin.__init__(self)
    id = Column(db.Integer, primary_key=True)
    immatriculation = Column(db.String(80), label=u'Immatriculation',
            description=u'Immatriculation du véhicule')
    modele = Column(db.String(255), label=u'Modèle', nullable=True,
            description=u'Modèle du véhicule')
    annee = Column(db.Integer, label=u'Année', nullable=True,
            description=u'Année de mise en production du véhicule')
    motorisation = Column(db.String(80), label=u'Motorisation', nullable=True,
            description=u'Motorisation du véhicule')
    puissance = Column(db.Float(), label=u'Puissance', nullable=True,
            description=u'Puissance du véhicule')
    type_ = Column(Enum('sedan', 'mpv', 'station_wagon', 'normal'), name='type_',
            label='Type', nullable=True)
    relais = Column(db.Boolean, label=u'Relais', default=False, nullable=True,
            description=u'Est-ce un véhicule relais')
    pmr = Column(db.Boolean, label=u'PMR', default=False, nullable=True,
            description=u'Le véhicule est il adapté aux PMR')
    marque = Column(db.String(255), label=u'Marque', nullable=True,
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
    luxary = Column(db.Boolean, name='luxary', label='Luxe ?', nullable=True)
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
    wifi = Column(db.Boolean, name='wifi', label=u'Wifi à bord ?',
            nullable=True)
    baby_seat = Column(db.Boolean, name='baby_seat', label=u'Siège bébé ?',
            nullable=True)
    bike_accepted = Column(db.Boolean, name='bike_accepted',
            label=u'Transport de vélo', nullable=True)
    pet_accepted = Column(db.Boolean, name='pet_accepted',
            label=u'Animaux de compagnie acceptés ?', nullable=True)
    AC_vehicle = Column(db.Boolean, name='AC_vehicle',
            label=u'Véhicule climatisé', nullable=True)
    telepeage = Column(db.Boolean, name='telepeage',
            label=u'Véhicule équipé du télépéage', nullable=True)
    gps = Column(db.Boolean, name='gps', label=u'Véhicule équipé d\'un GPS',
            nullable=True)
    conventionne = Column(db.Boolean, name='conventionne',
            label=u'Conventionné assurance maladie', nullable=True)
    every_destination = Column(db.Boolean, name='every_destination',
            label=u'Toute destination', nullable=True)
    color = Column(db.String(255), name='color', label='Couleur : ',
            nullable=True)
    snv = Column(db.Boolean, name='snv',
            label=u'Véhicule spécialement aménagé pour PMR ', nullable=True)

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

    public_fields = set(["numero", "marque", "modele", "immatriculation"])
    id = Column(db.Integer, primary_key=True)
    numero = Column(db.Integer, label=u'Numéro',
            description=u'Numéro de l\'ADS')
    doublage = Column(db.Boolean, label=u'Doublage', default=False,
            nullable=True, description=u'L\'ADS est elle doublée ?')
    nom_societe = Column(db.String(255), label=u'Nom de la société',
            default='', nullable=True,
            description=u'Nom de la société')
    artisan = Column(db.String(255), label=u'Nom de l\'artisan',
            default='', nullable=True,
            description=u'Nom de l\'artisan')
    personne = Column(db.String(255), label=u'Nom de la personne', default='',
            nullable=True,
            description=u'Nom de la personne')
    insee = Column(db.Integer, label=u'Code INSEE de la commune d\'attribution')
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)
    vehicle = db.relationship('Vehicle', backref='vehicle')

    def __repr__(self):
        return '<ADS %r>' % str(self.id)

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)


class Conducteur(db.Model, AsDictMixin, HistoryMixin):
    def __init__(self):
        db.Model.__init__(self)
        HistoryMixin.__init__(self)
    id = Column(db.Integer, primary_key=True)
    nom = Column(db.String(255), label='Nom', description=u'Nom du conducteur')
    prenom = Column(db.String(255), label=u'Prénom',
            description=u'Prénom du conducteur')
    date_naissance = Column(db.Date(),
        label=u'Date de naissance (format année-mois-jour)',
        description=u'Date de naissance (format année-mois-jour)')
    carte_pro = Column(db.String(),
            label=u'Numéro de la carte professionnelle',
            description=u'Numéro de la carte professionnelle')

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return '<conducteurs %r>' % str(self.id)
