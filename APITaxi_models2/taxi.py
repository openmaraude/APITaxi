from . import db
from .mixins import HistoryMixin


class Taxi(HistoryMixin, db.Model):

    def __repr__(self):
        return '<Taxi %s (vehicle %s, ADS %s, driver %s)>' % (
            self.id,
            self.vehicle_id,
            self.ads_id,
            self.driver_id
        )

    id = db.Column(db.String, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'))
    ads_id = db.Column(db.Integer, db.ForeignKey('ADS.id'))
    added_by_id = db.Column('added_by', db.Integer, db.ForeignKey('user.id'))
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'))
    rating = db.Column(db.Float)
    current_hail_id = db.Column(db.String, db.ForeignKey('hail.id', name='taxi_hail_id'))

    vehicle = db.relationship('Vehicle', lazy='raise')
    ads = db.relationship('ADS', lazy='raise')
    added_by = db.relationship('User', lazy='raise')
    driver = db.relationship('Driver', lazy='raise')
    current_hail = db.relationship('Hail', foreign_keys=[current_hail_id], lazy='raise')
