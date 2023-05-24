from . import db
from .mixins import HistoryMixin


OWNER_TYPES = ('company', 'individual')


class ADS(HistoryMixin, db.Model):
    __tablename__ = 'ADS'  # Flask-SQLAlchemy 3+ is lowercasing

    __table_args__ = (
        db.Index('ads_insee_index', 'insee'),
        db.Index('ads_numero_index', 'numero'),
        db.UniqueConstraint('numero', 'insee', 'added_by', name='unique_ads')
    )

    def __repr__(self):
        return '<ADS %s (numéro %s)>' % (self.id, self.numero)

    id = db.Column(db.Integer, primary_key=True)
    # numéro attribué à l'ADS par l'autorité de délivrance
    numero = db.Column(db.String, nullable=False)
    # double sortie journalière autorisée
    doublage = db.Column(db.Boolean, nullable=True)
    # code INSEE de la collectivité locale d'attribution
    insee = db.Column(db.String, nullable=False)
    # ADS avant 01/09/2014 ou après
    category = db.Column(db.String, nullable=False)
    # nom du titulaire de l'ADS
    owner_name = db.Column(db.String, nullable=False)
    # société/personne physique/ NR
    owner_type = db.Column(db.Enum(*OWNER_TYPES, name='owner_type_enum'), nullable=True)

    added_by_id = db.Column('added_by', db.Integer, db.ForeignKey('user.id'))
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'))

    added_by = db.relationship('User', lazy='raise')
    vehicle = db.relationship('Vehicle', lazy='raise')

    town = db.relationship('Town', primaryjoin='foreign(ADS.insee) == remote(Town.insee)', lazy='raise')
