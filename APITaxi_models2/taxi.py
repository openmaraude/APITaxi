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

    id = db.Column(db.String, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'))
    ads_id = db.Column(db.Integer, db.ForeignKey('ADS.id'))
    added_by_id = db.Column('added_by', db.Integer, db.ForeignKey('user.id'))
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'))
    rating = db.Column(db.Float)

    # There is a cyclic dependency between the tables Taxi and Hail through the
    # fields Taxi.current_hail_id and Hail.taxi_id.
    #
    # Due to a probable SQLAlchemy bug, the return value of
    # db.metadata.sorted_table is different when use_alter is set for at least
    # one of the two foreign keys:
    #
    # - if use_alter is set, the order is correct
    # - if not set, the order of the completely unrelated tables User, Role and
    #   RolesUsers is wrong. We expect the order to be [User, Role, RolesUsers]
    #   with RolesUsers at the end because it depends on the two previous
    #   models, whereas it is [User, RolesUsers, Role].
    #
    # use_alter is set because
    # APITaxi_models2.unittest.conftest.postgresql_empty rely on this order to
    # clear the database between tests.
    #
    # To know if use_alter can be removed with future SQLAlchemy releases, try
    # to remove it and see if unittests are passing. You should keep it if an
    # error is raised when tables are emptied after a test.
    current_hail_id = db.Column(
        db.String,
        db.ForeignKey('hail.id', name='taxi_hail_id', use_alter=True)
    )

    vehicle = db.relationship('Vehicle', lazy='raise')
    ads = db.relationship('ADS', lazy='raise')
    added_by = db.relationship('User', lazy='raise')
    driver = db.relationship('Driver', lazy='raise')
    current_hail = db.relationship('Hail', foreign_keys=[current_hail_id], lazy='raise')
