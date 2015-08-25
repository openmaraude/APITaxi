#coding: utf-8
from flask import current_app
from influxdb import InfluxDBClient

def get_client(dbname=None):
    c = current_app.config
    config = dict([(k, c.get('INFLUXDB_{}'.format(k.upper()), None)) for k in\
        ['host', 'port', 'username', 'password', 'ssl', 'verify_ssl', 'timeout',
            'use_udp', 'udp_port']])
    config['database'] = dbname
    return InfluxDBClient(**config)
