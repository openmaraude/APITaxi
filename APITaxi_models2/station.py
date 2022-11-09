from geoalchemy2 import Geography
from shapely.geometry import Point
from sqlalchemy import func

from . import db
from .mixins import HistoryMixin


class Station(HistoryMixin, db.Model):
    """A taxi station is where taxi drivers halt waiting for clients.

    The station can be located with three levels of precision:
    - a single point;
    - the polygon of the surface;
    - a multipolygon if the station is made of several parts.

    These locations and properties are provided by cities.
    """
    # Alembic doesn't detect GeoAlchemy2 spatial indexes are true by default
    __table_args__ = (
        db.Index('idx_station_location', 'location'),
    )

    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    town_id = db.Column(db.Integer, db.ForeignKey('town.id'), nullable=False)
    location = db.Column(Geography(geometry_type='GEOMETRY', srid=4326), nullable=False)
    address = db.Column(db.String, nullable=False)
    places = db.Column(db.Integer, nullable=False)
    call_number = db.Column(db.String(10), nullable=True)  # French format
    info = db.Column(db.String, nullable=False)

    town = db.relationship('Town', lazy='raise')
