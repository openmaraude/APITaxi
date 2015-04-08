# -*- coding: utf8 -*-
from backoffice_operateurs.models import db
from sqlalchemy_defaults import Column
from backoffice_operateurs.utils import AsDictMixin, HistoryMixin
from sqlalchemy.types import Enum

class ADS(db.Model, AsDictMixin, HistoryMixin):
    id = Column(db.Integer, primary_key=True)
    numero = Column(db.Integer, label=u'Numéro')
    immatriculation = Column(db.String(80), label=u'Immatriculation')
    modele = Column(db.String(255), label=u'Modèle', nullable=True)
    annee = Column(db.Integer, label=u'Année', nullable=True)
    motorisation = Column(db.String(80), label=u'Motorisation', nullable=True)
    puissance = Column(db.Float(), label=u'Puissance', nullable=True)
    doublage = Column(db.Boolean, label=u'Doublage', default=False,
            nullable=True)
    relais = Column(db.Boolean, label=u'Relais', default=False, nullable=True)
    pmr = Column(db.Boolean, label=u'PMR', default=False, nullable=True)
    marque = Column(db.String(255), label=u'Marque', nullable=True)
    horodateur = Column(db.String(255), label=u'Horodateur', nullable=True)
    taximetre = Column(db.String(255), label=u'Taximètre', nullable=True)
    date_dernier_ct = Column(db.Date(),
        label=u'Date du dernier CT (format année-mois-jour)')
    date_validite_ct = Column(db.Date(),
        label=u'Date de la fin de validité du CT (format année-mois-jour)')
    nom_societe = Column(db.String(255), label=u'Nom de la société',
            default='', nullable=True)
    artisan = Column(db.String(255), label=u'Nom de l\'artisan',
            default='', nullable=True)
    personne = Column(db.String(255), label=u'Nom de la personne', default='',
            nullable=True)
    ZUPC_id = Column(db.Integer, db.ForeignKey('ZUPC.id'))
    ZUPC = db.relationship('ZUPC', backref='ZUPC')
    last_update_at = Column(db.DateTime, nullable=True)
    type_ = Column(Enum('sedan', 'mpv', 'station_wagon', 'normal'), name='type',
            label='Type', nullable=True)
    luxary = Column(db.Boolean, name='luxary', label='Luxe ?')
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
    dvd_player = Column(db.Boolean, name='dvd_player', label='Lecteur DVD ?')
    wifi = Column(db.Boolean, name='wifi', label=u'Wifi à bord ?',
            nullable=True)
    baby_seat = Column(db.Boolean, name='baby_seat', label=u'Siège bébé ?')
    bike_accepted = Column(db.Boolean, name='bike_accepted',
            label=u'Transport de vélo', nullable=True)
    pet_accepted = Column(db.Boolean, name='pet_accepted',
            label=u'Animaux de compagnie acceptés ?', nullable=True)
    AC_vehicle = Column(db.Boolean, name='AC_vehicle',
            label=u'Véhicule climatisé', nullable=True)
    telepeage = Column(db.Boolean, name='telepeage',
            label=u'Véhicule équipé du télépéage', nullable=True)
    gps = Column(db.Boolean, name='gps', label=u'Véhicule équipé d\'un GPS')
    conventionne = Column(db.Boolean, name='conventionne',
            label=u'Conventionné assurance maladie', nullable=True)
    every_destination = Column(db.Boolean, name='every_destination',
            label=u'Toute destination', nullable=True)
    color = Column(db.String(255), name='color', label='Couleur : ')
    snv = Column(db.Boolean, name='snv', 
            label=u'Véhicule spécialement aménagé pour PMR ', nullable=True)

    def __repr__(self):
        return '<ADS %r>' % str(self.id)

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)


class Conducteur(db.Model, AsDictMixin, HistoryMixin):
    id = Column(db.Integer, primary_key=True)
    nom = Column(db.String(255), label='Nom')
    prenom = Column(db.String(255), label=u'Prénom')
    date_naissance = Column(db.Date(),
        label=u'Date de naissance (format année-mois-jour)')
    carte_pro = Column(db.String(), label=u'Numéro de la carte professionnelle')

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return '<conducteurs %r>' % str(self.id)
