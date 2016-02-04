#coding: utf-8

from ..extensions import redis_store, user_datastore, db, celery
from ..models.taxis import Taxi, parse_number
from ..models.administrative import ZUPC
from itertools import izip, ifilter, imap
from datetime import datetime, timedelta
from time import mktime
from parse import parse as base_parse
from flask import current_app
from APITaxi_utils import influx_db

def scan_as_list(match, redis_store):
    cursor = ''
    while cursor != 0:
        cursor, data = redis_store.scan(cursor=cursor, match=match, count=100)
        yield data

def filter_outoftime_values(operator_values, bound):
    f = lambda o_v: o_v[1] and o_v[1]['timestamp'] >= bound
    return filter(lambda operator_value: f(operator_value), operator_values)

def parse_operator_value(operator, s):
    if type(s) not in (str, unicode):
        return operator, None
    return operator, Taxi.parse_redis(s)

def get_data(taxi_ids, bound, redis_store):
    pipe = redis_store.pipeline()
    map(lambda k: pipe.hgetall(k), taxi_ids)
    parsed_values = map(lambda map_operator_v:\
        map(lambda o_v: parse_operator_value(*o_v), map_operator_v.iteritems()),
            pipe.execute())
    pipe.reset()
    filtered_value = map(lambda v: filter_outoftime_values(v, bound), parsed_values)
    zipped_value = izip(taxi_ids, filtered_value)
    return ifilter(lambda taxi_operator: len(taxi_operator[1]) > 0, zipped_value)

def store_active_taxis(frequency):
    now = datetime.now()
    bound_time -= timedelta(seconds=Taxi._ACTIVITY_TIMEOUT + frequency * 60)
    bound = mktime(bound_time.timetuple())
    map_operateur_zupc_nb_active = dict()
    map_zupc_nb_active = dict()
    for l in scan_as_list('taxi:*', redis_store):
        for taxi_id, v in get_data(l, bound, redis_store):
            taxi_id = taxi_id[5:] #We cut the "taxi:" part
            taxi_db = Taxi.get(taxi_id)
            if taxi_db is None:
                current_app.logger.error('Taxi: {}, not found in database'.format(
                    taxi_id))
                continue
            if taxi_db.ads is None:
                current_app.logger.error('Taxi: {} is invalid'.format(taxi_id))
                continue
            zupc = ZUPC.get(taxi_db.ads.zupc_id)
            zupc = zupc.parent
            if not zupc:
                current_app.logger.error('Unable to find zupc: {}'.format(
                    taxi_db.ads.zupc_id))
            zupc = zupc.insee
            if zupc not in map_zupc_nb_active:
                map_zupc_nb_active[zupc] = 0
            map_zupc_nb_active[zupc] += 1
            for operator, result in v:
                if operator not in map_operateur_zupc_nb_active:
                    u = user_datastore.find_user(email=operator)
                    if not u:
                        current_app.logger.error('User: {} not found'.format(operator))
                        continue
                    map_operateur_zupc_nb_active[operator] = dict()
                if not zupc:
                    current_app.logger.error('Unable to find zupc: {}'.format(
                        taxi_db.ads.zupc_id))
                if zupc not in map_operateur_zupc_nb_active[operator]:
                    map_operateur_zupc_nb_active[operator][zupc] = 0
                map_operateur_zupc_nb_active[operator][zupc] += 1

    client = influx_db.get_client(current_app.config['INFLUXDB_TAXIS_DB'])
    to_insert = []
    bucket_size = 100
    measurement_name = "nb_taxis_every_{}".format(frequency)
    for operator, zupc_active in map_operateur_zupc_nb_active.iteritems():
        for zupc, active in zupc_active.iteritems():
            to_insert.append(
                {
                    "measurement": measurement_name,
                    "tags": {
                        "operator": operator,
                        "zupc": zupc
                    },
                    "time": now.strftime('%Y%m%dT%H:%M:%SZ'),
                    "fields": {
                        "value": active
                    }
                }
            )
            if len(to_insert) == 100:
                current_app.logger.debug('To insert: {}'.format(to_insert))
                client.write_points(to_insert)
                to_insert = []
    for zupc, active in map_zupc_nb_active.iteritems():
        to_insert.append(
            {
                "measurement": measurement_name,
                "tags": {
                    "operator": "",
                    "zupc": zupc
                },
                "time": now.strftime('%Y%m%dT%H:%M:%SZ'),
                "fields": {
                    "value": active
                }
            }
        )
        if len(to_insert) == 100:
            current_app.logger.debug('To insert: {}'.format(to_insert))
            client.write_points(to_insert)
            to_insert = []

    current_app.logger.debug('To insert: {}'.format(to_insert))
    client.write_points(to_insert)
