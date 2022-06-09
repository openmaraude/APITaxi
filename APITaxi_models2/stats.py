"""
Quick'n dirty InfluxDB replacement
"""

from sqlalchemy import event, DDL

from . import db


class BaseStats(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.DateTime, nullable=False)
    value = db.Column(db.Integer, nullable=False)


class InseeMixin:
    insee = db.Column(db.String, nullable=False)


class ZupcMixin:
    zupc = db.Column(db.String, nullable=False)


class OperatorMixin:
    operator = db.Column(db.String, nullable=False)



class stats_minute(BaseStats):
    pass


class stats_minute_insee(BaseStats, InseeMixin):
    pass


class stats_minute_zupc(BaseStats, ZupcMixin):
    pass


class stats_minute_operator(BaseStats, OperatorMixin):
    pass


class stats_minute_operator_insee(BaseStats, OperatorMixin, InseeMixin):
    pass


class stats_minute_operator_zupc(BaseStats, OperatorMixin, ZupcMixin):
    pass


class stats_hour(BaseStats):
    pass


class stats_hour_insee(BaseStats, InseeMixin):
    pass


class stats_hour_zupc(BaseStats, ZupcMixin):
    pass


class stats_hour_operator(BaseStats, OperatorMixin):
    pass


class stats_hour_operator_insee(BaseStats, OperatorMixin, InseeMixin):
    pass


class stats_hour_operator_zupc(BaseStats, OperatorMixin, ZupcMixin):
    pass


class stats_day(BaseStats):
    pass


class stats_day_insee(BaseStats, InseeMixin):
    pass


class stats_day_zupc(BaseStats, ZupcMixin):
    pass


class stats_day_operator(BaseStats, OperatorMixin):
    pass


class stats_day_operator_insee(BaseStats, OperatorMixin, InseeMixin):
    pass


class stats_day_operator_zupc(BaseStats, OperatorMixin, ZupcMixin):
    pass


class stats_week(BaseStats):
    pass


class stats_week_insee(BaseStats, InseeMixin):
    pass


class stats_week_zupc(BaseStats, ZupcMixin):
    pass


class stats_week_operator(BaseStats, OperatorMixin):
    pass


class stats_week_operator_insee(BaseStats, OperatorMixin, InseeMixin):
    pass


class stats_week_operator_zupc(BaseStats, OperatorMixin, ZupcMixin):
    pass


__all__ = [classname for classname in locals() if classname.startswith('stats_')]


for classname in __all__:
    class_ = locals()[classname]
    event.listen(
        class_.__table__,
        'after_create',
        DDL(f"SELECT create_hypertable('{class_.__tablename__}', 'time');")
    )
