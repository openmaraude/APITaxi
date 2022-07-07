from geoalchemy2 import Geography
from shapely.geometry import Point
from sqlalchemy import func

from . import db
from .mixins import HistoryMixin


# Taxis halting under this distance from a station are considered parked at this station
WITHIN_STATION_RADIUS = 50


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

    @classmethod
    def find(cls, taxi_location):
        """Find the station the taxi is located at.
        A taxi is considered at a station within a radius around this station,
        as the driver is supposed to take clients only when waiting at this station.

        Parameters:
            taxi_location: shapely.geometry.Point or str in WKT format
        Returns:
            Station instance or None if not found
        """
        if isinstance(taxi_location, Point):
            taxi_location = taxi_location.wkb
        return db.session.query(cls).filter(
            # Consider the taxi is a circle of the given radius
            func.ST_DWithin(taxi_location, cls.location, WITHIN_STATION_RADIUS)
        ).order_by(
            func.ST_Distance(taxi_location, cls.location)
        ).first()
