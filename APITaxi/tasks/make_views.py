#coding: utf-8
from ..extensions import redis_store, user_datastore
from APITaxi_models.taxis import Taxi
from APITaxi_models.administrative import ZUPC
from itertools import izip, ifilter, imap
from datetime import datetime, timedelta
from time import mktime, time
from flask import current_app
from APITaxi_utils import influx_db

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
        if zupc.insee not in map_insee_nb_active:
            map_insee_nb_active[zupc.insee] = set()
        map_insee_nb_active[zupc.insee].add(taxi_id)
        if operator not in map_operateur_insee_nb_active:
            u = user_datastore.find_user(email=operator)
            if not u:
                current_app.logger.error('User: {} not found'.format(operator))
                continue
            map_operateur_insee_nb_active[operator] = dict()
        if zupc.insee not in map_operateur_insee_nb_active[operator]:
            map_operateur_insee_nb_active[operator][zupc.insee] = set()
        map_operateur_insee_nb_active[operator][zupc.insee].add(taxi_id)
        if operator not in map_operateur_nb_active:
            map_operateur_nb_active[operator] = set()
        map_operateur_nb_active[operator].add(taxi_id)

    client = influx_db.get_client(current_app.config['INFLUXDB_TAXIS_DB'])
    to_insert = []
    bucket_size = 100
    measurement_name = "nb_taxis_every_{}".format(frequency)
    def insert(operator, zupc, active):
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

    if len(to_insert) > 0:
        current_app.logger.debug('To insert: {}'.format(to_insert))
        client.write_points(to_insert)
