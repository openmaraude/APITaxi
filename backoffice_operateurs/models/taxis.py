# -*- coding: utf8 -*-
from backoffice_operateurs.models import db
from sqlalchemy_defaults import Column
from backoffice_operateurs.utils import AsDictMixin

class ADS(db.Model, AsDictMixin):
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
    added_by = Column(db.Integer, db.ForeignKey('user.id'))
    added_at = Column(db.DateTime)
    added_via = Column(db.Enum('form', 'api', name="sources"))
    source = Column(db.String(255))
    last_update_at = Column(db.DateTime, nullable=True)

    def __repr__(self):
        return '<ADS %r>' % str(self.id)

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)


class Conducteur(db.Model, AsDictMixin):
    id = Column(db.Integer, primary_key=True)
    nom = Column(db.String(255), label='Nom')
    prenom = Column(db.String(255), label=u'Prénom')
    date_naissance = Column(db.Date(),
        label=u'Date de naissance (format année-mois-jour)')
    carte_pro = Column(db.String(), label=u'Numéro de la carte professionnelle')
    added_by = Column(db.Integer, db.ForeignKey('user.id'))
    added_at = Column(db.DateTime)
    added_via = Column(db.Enum('form', 'api', name="sources"))
    source = Column(db.String(255))
    last_update_at = Column(db.DateTime, nullable=True)

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return '<conducteurs %r>' % str(self.id)
