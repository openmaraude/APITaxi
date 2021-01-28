from geoalchemy2 import Geography

from . import db


class ZUPC(db.Model):
    # The two indexes are duplicated. We only declare them to reflect the
    # database, but we will need to eventually remove at least one of them.
    __table_args__ = (
        db.Index('zupc_shape_idx', 'shape'),
        db.Index('zupc_shape_igx', 'shape')
    )

    def __repr__(self):
        return '<ZUPC %s (%s - %s)>' % (self.id, self.departement_id, self.nom)

    id = db.Column(db.Integer, primary_key=True)
    departement_id = db.Column(db.Integer, db.ForeignKey('departement.id'))
    nom = db.Column(db.String(255), nullable=False)
    insee = db.Column(db.String)
    parent_id = db.Column(db.Integer, db.ForeignKey('ZUPC.id'))

    shape = db.Column(Geography(geometry_type='MULTIPOLYGON', srid=4326, spatial_index=False))
    max_distance = db.Column(db.Integer)

    departement = db.relationship('Departement', lazy='raise')
    parent = db.relationship('ZUPC', remote_side=[id], lazy='raise')
