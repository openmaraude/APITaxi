"""
Quick'n dirty TimeScaleDB stats
"""

from sqlalchemy.dialects import postgresql
import geoalchemy2

from . import db
from .mixins import HistoryMixin


class BaseStats(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # needed by SLQAlchemy
    time = db.Column(db.DateTime, primary_key=True)
    value = db.Column(db.Integer, nullable=False)


class InseeMixin:
    insee = db.Column(db.String, nullable=False)


class ZupcMixin:
    zupc = db.Column(db.String, nullable=False)


class OperatorMixin:
    operator = db.Column(db.String, nullable=False)



class stats_minute(BaseStats):
    pass


class stats_minute_insee(BaseStats, InseeMixin):
    pass


class stats_minute_zupc(BaseStats, ZupcMixin):
    pass


class stats_minute_operator(BaseStats, OperatorMixin):
    pass


class stats_minute_operator_insee(BaseStats, OperatorMixin, InseeMixin):
    pass


class stats_minute_operator_zupc(BaseStats, OperatorMixin, ZupcMixin):
    pass


class stats_hour(BaseStats):
    pass


class stats_hour_insee(BaseStats, InseeMixin):
    pass


class stats_hour_zupc(BaseStats, ZupcMixin):
    pass


class stats_hour_operator(BaseStats, OperatorMixin):
    pass


class stats_hour_operator_insee(BaseStats, OperatorMixin, InseeMixin):
    pass


class stats_hour_operator_zupc(BaseStats, OperatorMixin, ZupcMixin):
    pass


class stats_day(BaseStats):
    pass


class stats_day_insee(BaseStats, InseeMixin):
    pass


class stats_day_zupc(BaseStats, ZupcMixin):
    pass


class stats_day_operator(BaseStats, OperatorMixin):
    pass


class stats_day_operator_insee(BaseStats, OperatorMixin, InseeMixin):
    pass


class stats_day_operator_zupc(BaseStats, OperatorMixin, ZupcMixin):
    pass


class stats_week(BaseStats):
    pass


class stats_week_insee(BaseStats, InseeMixin):
    pass


class stats_week_zupc(BaseStats, ZupcMixin):
    pass


class stats_week_operator(BaseStats, OperatorMixin):
    pass


class stats_week_operator_insee(BaseStats, OperatorMixin, InseeMixin):
    pass


class stats_week_operator_zupc(BaseStats, OperatorMixin, ZupcMixin):
    pass


class StatsHails(db.Model, HistoryMixin):
    __table_args__ = (
        db.PrimaryKeyConstraint('id', 'added_at', name='stats_hails_pkey'),
    )

    id = db.Column(db.String, nullable=False)
    status = db.Column(db.String, nullable=False)
    moteur = db.Column(db.String, nullable=False)
    operateur = db.Column(db.String, nullable=False)
    incident_customer_reason = db.Column(db.String)
    incident_taxi_reason = db.Column(db.String)
    session_id = db.Column(postgresql.UUID(as_uuid=True), nullable=False)
    reporting_customer = db.Column(db.Boolean)
    reporting_customer_reason = db.Column(db.String)
    insee = db.Column(db.String, nullable=True)  # In case not found
    taxi_hash = db.Column(db.String, nullable=True)  # Nullable as we inject archived hails
    # transition_log times
    received = db.Column(db.DateTime, nullable=True)
    sent_to_operator = db.Column(db.DateTime, nullable=True)
    received_by_operator = db.Column(db.DateTime, nullable=True)
    received_by_taxi = db.Column(db.DateTime, nullable=True)
    accepted_by_taxi = db.Column(db.DateTime, nullable=True)
    accepted_by_customer = db.Column(db.DateTime, nullable=True)
    declined_by_taxi = db.Column(db.DateTime, nullable=True)
    declined_by_customer = db.Column(db.DateTime, nullable=True)
    timeout_taxi = db.Column(db.DateTime, nullable=True)
    timeout_customer = db.Column(db.DateTime, nullable=True)
    incident_taxi = db.Column(db.DateTime, nullable=True)
    incident_customer = db.Column(db.DateTime, nullable=True)
    customer_on_board = db.Column(db.DateTime, nullable=True)
    finished = db.Column(db.DateTime, nullable=True)
    failure = db.Column(db.DateTime, nullable=True)
    # Distance from the taxi when the client hailed
    hail_distance = db.Column(db.Float, nullable=True)
    tags = db.Column(postgresql.JSONB)


class StatsSearches(db.Model):
    __table_args__ = (
        db.PrimaryKeyConstraint('id', 'added_at', name='stats_searches_pkey'),
    )

    id = db.Column(db.Integer, autoincrement=True, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    lat = db.Column(db.Float, nullable=False)
    insee = db.Column(db.String(5), nullable=False)
    town = db.Column(db.String, nullable=False)
    moteur = db.Column(db.String, nullable=False)
    taxis_found = db.Column(db.Integer, nullable=False)  # Found wihtin the wider radius
    closest_taxi = db.Column(db.Float)
    added_at = db.Column(db.DateTime, nullable=False)
    # Actually seen by the client (legal maximum radius, and taxis with a shorter custom radius)
    taxis_seen = db.Column(db.Integer, nullable=False)


__all__ = [classname for classname in locals() if classname.startswith('stats_')] + [
    'StatsHails',
    'StatsSearches',
]
