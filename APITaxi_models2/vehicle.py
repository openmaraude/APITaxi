from . import db
from .mixins import HistoryMixin


VEHICLE_STATUS = [
    'free',
    'answering',
    'occupied',
    'oncoming',
    'off'
]


class VehicleConstructor(db.Model):

    __tablename__ = 'constructor'

    def __repr__(self):
        return '<Constructor %s (%s)>' % (self.id, self.name)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)


class VehicleModel(db.Model):

    __tablename__ = 'model'

    def __repr__(self):
        return '<Model %s (%s)>' % (self.id, self.name)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)


class Vehicle(db.Model):

    def __repr__(self):
        return '<Vehicle %s (%s)>' % (self.id, self.licence_plate)

    id = db.Column(db.Integer, primary_key=True)
    licence_plate = db.Column(db.String(80), nullable=False, unique=True)

    descriptions = db.relationship('VehicleDescription', lazy='raise')


class VehicleDescription(HistoryMixin, db.Model):

    __table_args__ = (
        db.UniqueConstraint('vehicle_id', 'added_by', name='uq_vehicle_description'),
    )

    def __repr__(self):
        return '<VehicleDescription %s (of Vehicle %s)>' % (self.id, self.vehicle_id)

    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, db.ForeignKey(VehicleModel.id))
    constructor_id = db.Column(db.Integer, db.ForeignKey(VehicleConstructor.id))

    model_year = db.Column(db.Integer)
    engine = db.Column(db.String(80))
    horse_power = db.Column(db.Float)
    relais = db.Column(db.Boolean)
    horodateur = db.Column(db.String(255))
    taximetre = db.Column(db.String(255))
    date_dernier_ct = db.Column(db.Date)
    date_validite_ct = db.Column(db.Date)
    special_need_vehicle = db.Column(db.Boolean)
    type = db.Column('type_', db.Enum('sedan', 'mpv', 'station_wagon', 'normal', name='vehicle_enum'))
    luxury = db.Column(db.Boolean)
    credit_card_accepted = db.Column(db.Boolean)
    nfc_cc_accepted = db.Column(db.Boolean)
    amex_accepted = db.Column(db.Boolean)
    bank_check_accepted = db.Column(db.Boolean)
    fresh_drink = db.Column(db.Boolean)
    dvd_player = db.Column(db.Boolean)
    tablet = db.Column(db.Boolean)
    wifi = db.Column(db.Boolean)
    baby_seat = db.Column(db.Boolean)
    bike_accepted = db.Column(db.Boolean)
    pet_accepted = db.Column(db.Boolean)
    air_con = db.Column(db.Boolean)
    electronic_toll = db.Column(db.Boolean)
    gps = db.Column(db.Boolean)
    cpam_conventionne = db.Column(db.Boolean)
    every_destination = db.Column(db.Boolean)
    color = db.Column(db.String(255))
    vehicle_id = db.Column(db.Integer, db.ForeignKey(Vehicle.id))
    added_by_id = db.Column('added_by', db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.Enum(*VEHICLE_STATUS, name='status_vehicle_enum'))
    nb_seats = db.Column(db.Integer)
    internal_id = db.Column(db.String)

    added_by = db.relationship('User', lazy='raise')
    constructor = db.relationship(VehicleConstructor, lazy='raise')
    model = db.relationship(VehicleModel, lazy='raise')
    vehicle = db.relationship(Vehicle, lazy='raise')
