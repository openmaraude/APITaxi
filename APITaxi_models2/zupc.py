from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import synonym

from . import db, mixins


# A given town can be part of several ZUPC
town_zupc = db.Table(
    'town_zupc', db.metadata,
    db.Column('town_id', db.Integer, db.ForeignKey('town.id')),
    db.Column('zupc_id', db.Integer, db.ForeignKey('ZUPC.id')),
    db.PrimaryKeyConstraint('town_id', 'zupc_id', name='town_zupc_pk'),
)


class Exclusion(db.Model):
    """Zones like airports may have different regulations about taxis."""
    __table_args__ = (
        db.Index('idx_exclusion_shape', 'shape'),
    )

    def __repr__(self):
        return f'<Exclusion {self.id} - {self.insee} ({self.name})>'

    id = db.Column(db.String, primary_key=True)  # OpenStreetMap ID
    name = db.Column(db.String(255), nullable=False)
    shape = db.Column(Geography(geometry_type='MULTIPOLYGON', srid=4326), nullable=False)


class Town(db.Model):
    """All the French towns, whether they are part of a ZUPC or not."""
    __table_args__ = (
        db.Index('idx_town_shape', 'shape'),
    )

    def __repr__(self):
        return f'<Town {self.id} - {self.insee} ({self.name})>'

    id = db.Column(db.Integer, primary_key=True)
    insee = db.Column(db.String(5), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    # 4326, also known as WGS84 is the standard also used in the GPS
    shape = db.Column(Geography(geometry_type='MULTIPOLYGON', srid=4326), nullable=False)

    allowed = db.relationship('ZUPC', secondary=town_zupc, viewonly=True)


class ZUPC(db.Model):
    """An actual ZUPC as created by an administrative decree.

    Towns are now in a separate model above.
    """

    def __repr__(self):
        return f'<ZUPC {self.id} ({self.nom})>'

    id = db.Column(db.Integer, primary_key=True)
    # The UUID comes from the ZUPC repo
    zupc_id = db.Column(postgresql.UUID, nullable=False, unique=True)

    nom = db.Column(db.String(255), nullable=False)
    name = synonym('nom')

    # Taxis from these towns are allowed to accept customer hails in this zone
    allowed = db.relationship('Town', secondary=town_zupc)


class Conurbation(mixins.HistoryMixin, db.Model):
    """A conurbation, or metropolis, is a big town, and its surroundings,
    seen as one administrative entity.
    """

    def __repr__(self):
        return f'<Conurbation of {self.id}>'

    # Mmemonic like "lyon" or "grenoble"
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    # Don't make another foreign key to towns, we just want the list of city codes
    members = db.Column(postgresql.ARRAY(db.String(5)))
