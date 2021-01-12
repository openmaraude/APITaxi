from . import db
from .mixins import HistoryMixin


OWNER_TYPES = ('company', 'individual')


class ADS(HistoryMixin, db.Model):

    __table_args__ = (
        db.Index('ads_insee_index', 'insee'),
        db.Index('ads_numero_index', 'numero'),
        db.UniqueConstraint('numero', 'insee', 'added_by', name='unique_ads')
    )

    def __repr__(self):
        return '<ADS %s (numéro %s)>' % (self.id, self.numero)

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String, nullable=False)
    doublage = db.Column(db.Boolean, nullable=True)
    added_by_id = db.Column('added_by', db.Integer, db.ForeignKey('user.id'))
    insee = db.Column(db.String, nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'))
    category = db.Column(db.String, nullable=False)
    owner_name = db.Column(db.String, nullable=False)
    owner_type = db.Column(db.Enum(*OWNER_TYPES, name='owner_type_enum'), nullable=True)
    zupc_id = db.Column(db.Integer, db.ForeignKey('ZUPC.id'), nullable=False)

    added_by = db.relationship('User', lazy='raise')
    vehicle = db.relationship('Vehicle', lazy='raise')
    zupc = db.relationship('ZUPC', lazy='raise')
