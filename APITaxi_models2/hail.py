from sqlalchemy import func
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.mutable import MutableList

from . import db
from .mixins import HistoryMixin


# These status are "terminal": the hail is considered over, and you cannot
# change the status to another one.
HAIL_TERMINAL_STATUS = (
    'failure',
    'declined_by_taxi',
    'incident_taxi',
    'timeout_taxi',
    'declined_by_customer',
    'timeout_customer',
    'timeout_accepted_by_customer',
    'finished',
)

# All possible hail status
HAIL_STATUS = (
    'received',
    'sent_to_operator',
    'received_by_operator',
    'received_by_taxi',
    'accepted_by_taxi',
    'accepted_by_customer',
    'customer_on_board',
    'incident_customer',
) + HAIL_TERMINAL_STATUS

REPORTING_CUSTOMER_REASONS = (
    'ko',  # Kept for backwards compatibility but not documented, 'no_show' is preferred
    'payment', 'courtesy', 'route', 'cleanliness', 'late', 'aggressive', 'no_show'
)

INCIDENT_CUSTOMER_REASONS = (
    '', 'mud_river', 'parade', 'earthquake',  # test values to ignore
    'no_show',  # The taxi didn't show
    'no_specs',  # The taxi doesn't have the characteristics announced
)

INCIDENT_TAXI_REASONS = (
    'no_show',  # The customer didn't show at the address
    'address',  # Address cannot be found
    'traffic',  # Slowed down by traffic
    'breakdown',  # Vehicle broke down
    'traffic_jam',  # Stuck in a traffic jam
    'garbage_truck',  # Stuck behind a garbage truck or other vehicle blocking the road
)

RATING_RIDE_REASONS = (
    'ko', 'payment', 'courtesy', 'route', 'cleanliness', 'late',
    'no_credit_card', 'bad_itinerary', 'dirty_taxi', 'automatic_rating'
)


class Hail(HistoryMixin, db.Model):

    __table_args__ = (
        db.ForeignKeyConstraint(
            ('customer_id', 'added_by'),
            ('customer.id', 'customer.added_by'), name='hail_customer_id'),
    )

    id = db.Column(db.String, primary_key=True)

    creation_datetime = db.Column(db.DateTime, nullable=False)
    taxi_id = db.Column(db.String, db.ForeignKey('taxi.id', name='hail_taxi_relation', deferrable=True), nullable=False)
    status = db.Column(db.Enum(*HAIL_STATUS, name='hail_status'), nullable=False)
    last_status_change = db.Column(db.DateTime)
    customer_id = db.Column(db.String, nullable=False)
    customer_lat = db.Column(db.Float, nullable=False)
    customer_lon = db.Column(db.Float, nullable=False)
    operateur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    added_by_id = db.Column('added_by', db.Integer, db.ForeignKey('user.id'))
    customer_address = db.Column(db.String, nullable=False)
    customer_phone_number = db.Column(db.String, nullable=False)
    taxi_phone_number = db.Column(db.String, server_default='', nullable=False)
    reporting_customer = db.Column(db.Boolean)
    reporting_customer_reason = db.Column(db.Enum(*REPORTING_CUSTOMER_REASONS, name='reporting_customer_reason_enum'))
    incident_customer_reason = db.Column(db.Enum(*INCIDENT_CUSTOMER_REASONS, name='incident_customer_reason_enum'))
    incident_taxi_reason = db.Column(db.Enum(*INCIDENT_TAXI_REASONS, name='incident_taxi_reason_enum'))
    rating_ride_reason = db.Column(db.Enum(*RATING_RIDE_REASONS, name='reason_ride_enum'))
    rating_ride = db.Column(db.Integer)
    initial_taxi_lat = db.Column(db.Float)
    initial_taxi_lon = db.Column(db.Float)

    session_id = db.Column(
        postgresql.UUID(as_uuid=True), nullable=False, server_default=func.uuid_generate_v4()
    )

    # Record status changes (manually)
    transition_log = db.Column(MutableList.as_mutable(postgresql.JSON()), nullable=False, server_default="[]")

    # Blurring hail personal data, first step before archiving
    blurred = db.Column(db.Boolean, nullable=True, server_default='false')

    # Relationships
    added_by = db.relationship('User', foreign_keys=[added_by_id], lazy='raise')
    customer = db.relationship('Customer', foreign_keys=[customer_id], lazy='raise')
    operateur = db.relationship('User', foreign_keys=[operateur_id], lazy='raise')
    taxi = db.relationship('Taxi', foreign_keys=[taxi_id], lazy='raise')
