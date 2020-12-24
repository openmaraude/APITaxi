from . import db
from .mixins import HistoryMixin


class Driver(HistoryMixin, db.Model):

    __table_args__ = (
        db.Index('driver_departement_id_idx', 'departement_id'),
        db.Index('driver_professional_licence_idx', 'professional_licence'),
    )

    def __repr__(self):
        return '<Driver %s (%s %s)>' % (self.id, self.first_name, self.last_name)

    id = db.Column(db.Integer, primary_key=True)

    departement_id = db.Column(db.Integer, db.ForeignKey('departement.id'))
    added_by_id = db.Column('added_by', db.Integer, db.ForeignKey('user.id'))
    birth_date = db.Column(db.Date)
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    professional_licence = db.Column(db.String, nullable=False)

    added_by = db.relationship('User', lazy='raise')
    departement = db.relationship('Departement', lazy='raise')
