from . import db
from .mixins import HistoryMixin


UPDATABLE_VEHICLE_STATUS = [
    'free',
    'occupied',
    'off'
]

# VEHICLE_STATUS = statuses operator can update + statuses workers
# automatically update.
VEHICLE_STATUS = UPDATABLE_VEHICLE_STATUS + [
    'answering',
    'oncoming',
]


class Vehicle(db.Model):

    __table_args__ = (
        db.UniqueConstraint('licence_plate', name='unique_vehicle'),
    )

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
        return '<VehicleDescription %s (of Vehicle %s added by %s)>' % (
            self.id, self.vehicle_id, self.added_by_id
        )

    id = db.Column(db.Integer, primary_key=True)

    model = db.Column(db.String, nullable=False, server_default='')
    constructor = db.Column(db.String, nullable=False, server_default='')

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

    added_by = db.relationship('User', lazy='raise')
    vehicle = db.relationship(Vehicle, lazy='raise')

    @property
    def characteristics(self):
        return [
            field for field in (
                'special_need_vehicle',
                'every_destination',
                'gps',
                'electronic_toll',
                'air_con',
                'pet_accepted',
                'bike_accepted',
                'baby_seat',
                'wifi',
                'tablet',
                'dvd_player',
                'fresh_drink',
                'amex_accepted',
                'bank_check_accepted',
                'nfc_cc_accepted',
                'credit_card_accepted',
                'luxury'
            ) if getattr(self, field)
        ]