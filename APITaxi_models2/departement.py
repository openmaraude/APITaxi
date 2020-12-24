from . import db


class Departement(db.Model):
    # This index is a duplicate since numero is unique so already indexed. We
    # only declare it to reflect the database, but we will need to eventually
    # remove it.
    __table_args__ = (
        db.Index('departement_numero_index', 'numero'),
    )

    def __repr__(self):
        return '<Departement %s (%s - %s)>' % (self.id, self.numero, self.nom)

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(255), nullable=False)
    numero = db.Column(db.String, nullable=False, unique=True)
