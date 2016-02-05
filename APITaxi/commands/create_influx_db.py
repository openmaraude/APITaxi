#coding: utf-8
from . import manager
from APITaxi_utils import influx_db

@manager.command
def create_influx_db(dbname):
    c = influx_db.get_client()
    c.create_database(dbname)
