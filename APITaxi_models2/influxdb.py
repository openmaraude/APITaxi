"""
Quick'n dirty InfluxDB replacement

TODO remove
"""

from . import db


class nb_taxis_every(db.Model):

    __table_args__ = (
        # We should just need to filter by a given measurement, and order by time
        db.Index('nb_taxis_every_time', 'time', 'measurement'),
    )

    def __repr__(self):
        tags = {}
        if self.insee:
            tags['insee'] = self.insee
        if self.zupc:
            tags['zupc'] = self.zupc
        if self.operator:
            tags['operator'] = self.operator
        return "<nb_taxis_every({0.measurement}) time={0.time} value={0.value} tags={1}>".format(self, tags)

    measurement = db.Column(db.Integer, nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    value = db.Column(db.Integer, nullable=False)
    insee = db.Column(db.String, nullable=True)
    zupc = db.Column(db.String, nullable=True)
    operator = db.Column(db.String, nullable=True)

    # The model itself doesn't have a primary key, but the ORM needs one,
    # and each combination must be unique
    __mapper_args__ = {
        'primary_key': [time, measurement, insee, zupc, operator]
    }
