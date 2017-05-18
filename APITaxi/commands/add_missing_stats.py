#coding: utf-8
from . import manager
from APITaxi_utils import influx_db
from APITaxi_models import Hail
from APITaxi_models.security import User
from flask import current_app
from sqlalchemy import or_

@manager.command
def add_missing_stats():
    c = influx_db.get_client(current_app.config['INFLUXDB_TAXIS_DB'])
    r = c.query("select value from hails_status_changed_with_id ORDER BY time LIMIT 1;")
    min_time = r.get_points().next()['time']
    fields = [
        'change_to_sent_to_operator',
        'change_to_received_by_operator',
        'change_to_received_by_taxi',
        'change_to_accepted_by_taxi',
        'change_to_accepted_by_customer',
        'change_to_declined_by_taxi',
        'change_to_declined_by_customer',
        'change_to_incident_taxi',
        'change_to_incident_customer',
        'change_to_timeout_taxi',
        'change_to_timeout_customer',
        'change_to_failure',
        'change_to_finished',
        'change_to_customer_on_board',
        'change_to_timeout_accepted_by_customer',
    ]
    q = Hail.query.filter(Hail.added_at <= min_time, or_(*[getattr(Hail, f) != None for f in fields]))
    for h in q.all():
        previous_status = None
        statuses = [(f[len("change_to_"):], getattr(h, f)) for f in fields]
        statuses = filter(lambda v: v[1], statuses)
        statuses = sorted(statuses, key=lambda v: v[1])
        for status in statuses:
            c.write_points([{"measurement" : "hails_status_changed_with_id",
                             "tags": {
                                  "added_by": User.query.get(h.added_by).email,
                                  "operator": h.operateur.email,
                                  "zupc": h.taxi_relation.ads.zupc.parent.insee,
                                  "previous_status": previous_status,
                                  "status": status[0],
                                  "hail_id": h.id
                              },
                              "time": status[1].strftime('%Y%m%dT%H:%M:%SZ'),
                              "fields": {"value": 1}
                          }]
            )
            previous_status = status[0]
