from . import db
from .mixins import HistoryMixin


class Customer(HistoryMixin, db.Model):

    def __repr__(self):
        return '<Customer %s (moteur id %s)>' % (self.id, self.moteur_id)

    id = db.Column(db.String, primary_key=True)
    moteur_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    added_by_id = db.Column('added_by', db.Integer, db.ForeignKey('user.id'))
    ban_begin = db.Column(db.DateTime)
    ban_end = db.Column(db.DateTime)
    phone_number = db.Column(db.String)
    reprieve_begin = db.Column(db.DateTime)
    reprieve_end = db.Column(db.DateTime)

    moteur = db.relationship('User', foreign_keys=[moteur_id], lazy='raise')
    added_by = db.relationship('User', foreign_keys=[added_by_id], lazy='raise')
