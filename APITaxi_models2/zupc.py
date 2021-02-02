from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql

from . import db


class Town(db.Model):
    """All the French towns, whether they are part of a ZUPC or not."""

    def __repr__(self):
        return f'<Town {self.id} - {self.insee} ({self.name})>'

    id = db.Column(db.Integer, primary_key=True)
    insee = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    # 4326, also known as WGS84 is the standard also used in the GPS
    shape = db.Column(Geography(geometry_type='MULTIPOLYGON', srid=4326), nullable=False)


class ZUPC(db.Model):
    # The two indexes are duplicated. We only declare them to reflect the
    # database, but we will need to eventually remove at least one of them.
    __table_args__ = (
        db.Index('zupc_shape_idx', 'shape'),
        db.Index('zupc_shape_igx', 'shape')
    )

    def __repr__(self):
        return '<ZUPC %s (%s - %s)>' % (self.id, self.insee, self.nom)

    id = db.Column(db.Integer, primary_key=True)
    # The UUID comes from the ZUPC repo
    zupc_id = db.Column(postgresql.UUID, nullable=True)
    nom = db.Column(db.String(255), nullable=False)
    insee = db.Column(db.String)
    parent_id = db.Column(db.Integer, db.ForeignKey('ZUPC.id'))

    shape = db.Column(Geography(geometry_type='MULTIPOLYGON', srid=4326, spatial_index=False))

    parent = db.relationship('ZUPC', remote_side=[id], lazy='raise')
