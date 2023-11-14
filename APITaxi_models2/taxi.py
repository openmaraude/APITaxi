from . import db
from .mixins import HistoryMixin


class Taxi(HistoryMixin, db.Model):

    def __repr__(self):
        return '<Taxi %s (vehicle %s, ADS %s, driver %s, added_by %s)>' % (
            self.id,
            self.vehicle_id,
            self.ads_id,
            self.driver_id,
            self.added_by_id
        )

    __table_args__ = (
        db.UniqueConstraint('vehicle_id', 'ads_id', 'driver_id', 'added_by', name='unique_taxi'),
    )

    id = db.Column(db.String, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'))
    ads_id = db.Column(db.Integer, db.ForeignKey('ADS.id'))
    added_by_id = db.Column('added_by', db.Integer, db.ForeignKey('user.id'))
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'))
    rating = db.Column(db.Float)

    vehicle = db.relationship('Vehicle', lazy='raise')
    ads = db.relationship('ADS', lazy='raise')
    added_by = db.relationship('User', lazy='raise')
    driver = db.relationship('Driver', lazy='raise')
