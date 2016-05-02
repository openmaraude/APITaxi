#coding: utf-8
from ..extensions import redis_store, user_datastore
from APITaxi_models.taxis import Taxi
from APITaxi_models.administrative import ZUPC
from itertools import izip, ifilter, imap
from datetime import datetime, timedelta
from time import mktime, time
from flask import current_app
from APITaxi_utils import influx_db
from itertools import izip_longest, compress

def store_active_taxis(frequency):
    now = datetime.utcnow()
    bound = time() - (Taxi._ACTIVITY_TIMEOUT + frequency * 60)
    map_operateur_insee_nb_active = dict()
    map_operateur_nb_active = dict()
    map_insee_nb_active = dict()
    active_taxis = set()
    insee_zupc_dict = dict()
    prefixed_taxi_ids = []
    convert = lambda d: mktime(d.timetuple())
    for taxi_id_operator in redis_store.zrangebyscore(
            current_app.config['REDIS_TIMESTAMPS'], bound, time()):
        taxi_id, operator = taxi_id_operator.split(':')
        active_taxis.add(taxi_id)
        taxi_db = Taxi.query.get(taxi_id)
        if taxi_db is None:
            current_app.logger.error('Taxi: {}, not found in database'.format(
                taxi_id))
            continue
        if taxi_db.ads is None:
            current_app.logger.error('Taxi: {} is invalid'.format(taxi_id))
            continue
#This a cache for insee to zupc.
        if not taxi_db.ads.insee in insee_zupc_dict:
            zupc = ZUPC.query.get(taxi_db.ads.zupc_id)
            if not zupc:
                current_app.logger.error('Unable to find zupc: {}'.format(
                    taxi_db.ads.zupc_id))
            zupc = zupc.parent
            insee_zupc_dict[zupc.insee] = zupc
            insee_zupc_dict[taxi_db.ads.insee] = zupc
        else:
            zupc = insee_zupc_dict[taxi_db.ads.insee]
        map_insee_nb_active.setdefault(zupc.insee, set()).add(taxi_id)
        if operator not in map_operateur_insee_nb_active:
            u = user_datastore.find_user(email=operator)
            if not u:
                current_app.logger.error('User: {} not found'.format(operator))
                continue
            map_operateur_insee_nb_active[operator] = dict()
        map_operateur_insee_nb_active[operator].setdefault(zupc.insee, set()).add(taxi_id)
        map_operateur_nb_active.setdefault(operator, set()).add(taxi_id)

    map_operateur_insee_nb_available = dict()
    map_operateur_nb_available = dict()

    available_ids = set()
    for operator, insee_taxi_ids in map_operateur_insee_nb_active.iteritems():
        for insee, taxis_ids in insee_taxi_ids.iteritems():
            for ids in izip_longest(*[taxis_ids]*100, fillvalue=None):
                pipe = redis_store.pipeline()
                for id_ in ids_:
                    pipe.sismember(current_app.config['REDIS_TIMESTAMPS'],
                                   i+':'+operator)
                res = compress(ids, pipe.execute())
                map_operateur_insee_nb_available(operator, dict()).setdefault(
                    insee, set()).union(set(res))
                available_ids.union(set(res))

    for operateur, taxis_ids in map_operateur_nb_active.iteritems():
        map_operateur_nb_active.setdefault(operateur, set()).union(
            set([t+':'+operateur for t in taxis_ids]).intersection(avaliable_ids
                )
        )


    client = influx_db.get_client(current_app.config['INFLUXDB_TAXIS_DB'])
    to_insert = []
    bucket_size = 100
    def insert(operator, zupc, active, available=False):
        measurement_name = "nb_taxis_every_{}".format(frequency)
        if available:
            measurement_name += '_available'
        to_insert.append({
                    "measurement": measurement_name,
                    "tags": {
                        "operator": operator,
                        "zupc": zupc
                    },
                    "time": now.strftime('%Y%m%dT%H:%M:%SZ'),
                    "fields": {
                        "value": len(active)
                    }
                }
        )
        if len(to_insert) == 100:
            current_app.logger.debug('To insert: {}'.format(to_insert))
            client.write_points(to_insert)
            to_insert[:] = []

    for operator, zupc_active in map_operateur_insee_nb_active.iteritems():
        for zupc, active in zupc_active.iteritems():
            insert(operator, zupc, active)

    for zupc, active in map_insee_nb_active.iteritems():
        insert("", zupc, active)

    for operateur, active in map_operateur_nb_active.iteritems():
        insert(operateur, "", active)

    insert("", "", active_taxis)

    for operator, zupc_available in map_operateur_insee_nb_active.iteritems():
        for zupc, available in zupc_active.iteritems():
            insert(operator, zupc, available, True)

    for zupc, available in map_insee_nb_active.iteritems():
        insert("", zupc, available, True)

    if len(to_insert) > 0:
        current_app.logger.debug('To insert: {}'.format(to_insert))
        client.write_points(to_insert)
