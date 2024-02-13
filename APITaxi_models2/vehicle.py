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

    descriptions = db.relationship('VehicleDescription', lazy='raise', viewonly=True)


class VehicleDescription(HistoryMixin, db.Model):

    __table_args__ = (
        db.UniqueConstraint('vehicle_id', 'added_by', name='uq_vehicle_description'),
    )

    def __repr__(self):
        return '<VehicleDescription %s (of Vehicle %s added by %s)>' % (
            self.id, self.vehicle_id, self.added_by_id
        )

    id = db.Column(db.Integer, primary_key=True)

    # modèle du véhicule
    model = db.Column(db.String, nullable=False, server_default='')
    # constructeur du véhicule
    constructor = db.Column(db.String, nullable=False, server_default='')
    # motorisation
    engine = db.Column(db.String(80), server_default='', nullable=False)
    # couleur du véhicule
    color = db.Column(db.String(255), server_default='', nullable=False)
    # nombre de places
    nb_seats = db.Column(db.Integer)
    # véhicule relais au sens de l'article R.3121-2 du code des transports
    relais = db.Column(db.Boolean)

    # characteristics
    # équipé American Express
    amex_accepted = db.Column(db.Boolean)
    # chèques bancaires français acceptés
    bank_check_accepted = db.Column(db.Boolean)
    # wifi à bord
    wifi = db.Column(db.Boolean)
    # siège bébé disponible
    baby_seat = db.Column(db.Boolean)
    # vélos acceptés
    bike_accepted = db.Column(db.Boolean)
    # animaux de compagnie acceptés
    pet_accepted = db.Column(db.Boolean)
    # Catégorie VASP (J1) handicap (J3) sur la carte grise
    vasp_handicap = db.Column(db.Boolean)

    vehicle_id = db.Column(db.Integer, db.ForeignKey(Vehicle.id))
    added_by_id = db.Column('added_by', db.Integer, db.ForeignKey('user.id'))

    # The following are to be deleted TODO
    air_con = db.Column(db.Boolean)
    horodateur = db.Column(db.String(255), server_default='', nullable=False)
    date_dernier_ct = db.Column(db.Date)
    date_validite_ct = db.Column(db.Date)
    credit_card_accepted = db.Column(db.Boolean)  # Became mandatory
    electronic_toll = db.Column(db.Boolean)
    fresh_drink = db.Column(db.Boolean)
    tablet = db.Column(db.Boolean)
    dvd_player = db.Column(db.Boolean)
    taximetre = db.Column(db.String(255), server_default='', nullable=False)
    every_destination = db.Column(db.Boolean)
    nfc_cc_accepted = db.Column(db.Boolean)  # NFC credit card? should be the norm
    special_need_vehicle = db.Column(db.Boolean)
    gps = db.Column(db.Boolean)
    luxury = db.Column(db.Boolean)
    horse_power = db.Column(db.Float)
    model_year = db.Column(db.Integer)
    type = db.Column('type_', db.Enum('sedan', 'mpv', 'station_wagon', 'normal', name='vehicle_enum'))
    cpam_conventionne = db.Column(db.Boolean)

    # Live data
    status = db.Column(db.Enum(*VEHICLE_STATUS, name='status_vehicle_enum'))
    radius = db.Column(db.Integer, nullable=True)

    added_by = db.relationship('User', lazy='raise')
    vehicle = db.relationship(Vehicle, lazy='raise')

    @property
    def characteristics(self):
        return [
            field for field in (
                'pet_accepted',
                'bike_accepted',
                'baby_seat',
                'wifi',
                'vasp_handicap',
                'amex_accepted',
                'bank_check_accepted',
            ) if getattr(self, field)
        ]
