from . import db
from .mixins import HistoryMixin


class Driver(HistoryMixin, db.Model):

    __table_args__ = (
        db.Index('driver_departement_id_idx', 'departement_id'),
        db.Index('driver_professional_licence_idx', 'professional_licence'),
        db.UniqueConstraint('departement_id', 'professional_licence', 'added_by', name='unique_driver')
    )

    def __repr__(self):
        return '<Driver %s (%s %s)>' % (self.id, self.first_name, self.last_name)

    id = db.Column(db.Integer, primary_key=True)

    # département d'exercice du conducteur
    departement_id = db.Column(db.Integer, db.ForeignKey('departement.id'), nullable=False)
    added_by_id = db.Column('added_by', db.Integer, db.ForeignKey('user.id'))
    # date de naissance du conducteur
    birth_date = db.Column(db.Date)
    # prénom du conducteur
    first_name = db.Column(db.String(255), nullable=False)
    # nom du conducteur
    last_name = db.Column(db.String(255), nullable=False)
    # n° carte professionnelle
    professional_licence = db.Column(db.String, nullable=False)

    added_by = db.relationship('User', lazy='raise')
    departement = db.relationship('Departement', lazy='raise')
