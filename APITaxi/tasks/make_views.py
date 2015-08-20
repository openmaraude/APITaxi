#coding: utf-8

from ..extensions import redis_store, user_datastore, db, celery
from ..models.taxis import Taxi
from ..models.stats import ActiveTaxis
from itertools import izip, ifilter, imap
from datetime import datetime, timedelta
from time import mktime
from parse import parse as base_parse
from flask import current_app
from ..utils import influx_db

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
    return operator, base_parse(Taxi._FORMAT_OPERATOR, s)

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

def store_active_taxis():
    current_app.logger.info('store_active_taxis')
    bound_time = datetime.now() - timedelta(minutes=15)
    bound = mktime(bound_time.timetuple())
    map_operateur_zupc_nb_active = dict()
    for l in scan_as_list('taxi:*', redis_store):
        for taxi_id, v in get_data(l, bound, redis_store):
            taxi_id = taxi_id[5:] #We cut the "taxi:" part
            taxi_db = Taxi.get(taxi_id)
            if taxi_db is None:
                current_app.logger.error('Taxi: {}, not found in database'.format(taxi_id))
                continue
            for operator, result in v:
                u = user_datastore.find_user(email=operator)
                if not u:
                    current_app.logger.error('User: {} not found'.format(operator))
                    continue
                if u.id not in map_operateur_zupc_nb_active:
                    map_operateur_zupc_nb_active[u.id] = dict()
                if taxi_db.ads.zupc_id not in map_operateur_zupc_nb_active[u.id]:
                    map_operateur_zupc_nb_active[u.id][taxi_db.ads.zupc_id] = 0
                map_operateur_zupc_nb_active[u.id][taxi_db.ads.zupc_id] += 1

    client = influx_db.get_client('taxis')
    to_insert = []
    bucket_size = 100
    for operator, zupc_active in map_operateur_zupc_nb_active.iteritems():
        for zupc, active in zupc_active.iteritems():
            to_insert.append(
                {
                    "measurement": "nb_taxis",
                    "tags": {
                        "operator": user_datastore.get_user(operator).email,
                        "zupc": zupc
                    },
                    "time": datetime.utcnow().strftime('%Y%m%dT%H:%M:%SZ'),
                    "fields": {
                        "value": active
                    }
                }
            )
            if len(to_insert) == 100:
                current_app.logger.info('To insert: {}'.format(to_insert))
                client.write_points(to_insert)
                to_insert = []
    current_app.logger.info('To insert: {}'.format(to_insert))
    client.write_points(to_insert)
