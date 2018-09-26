#coding: utf-8
from . import manager
from APITaxi_utils import influx_db

@manager.command
def create_influx_db(dbname):
    c = influx_db.get_client(current_app.config['INFLUXDB_TAXIS_DB'])
    if c:
        c.create_database(dbname)
    else:
        print("There is no client")
