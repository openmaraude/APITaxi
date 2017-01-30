from . import manager
def warm_up_redis_func(app=None, db=None, user_model=None, redis_store=None):
    not_available = set()
    available = set()
    cur = db.session.connection().connection.cursor()
    cur.execute("""
    SELECT taxi.id AS taxi_id, vd.status, vd.added_by FROM taxi
    LEFT OUTER JOIN vehicle ON vehicle.id = taxi.vehicle_id
    LEFT OUTER JOIN vehicle_description AS vd ON vehicle.id = vd.vehicle_id
    """)
    users = {u.id: u.email for u in user_model.query.all()}
    for taxi_id, status, added_by in cur.fetchall():
        user = users.get(added_by)
        taxi_id_operator = "{}:{}".format(taxi_id, user)
        if status == 'free':
            available.add(taxi_id_operator)
        else:
            not_available.add(taxi_id_operator)
    to_remove = list()
    if redis_store.type(app.config['REDIS_NOT_AVAILABLE']) != 'zset':
        redis_store.delete(app.config['REDIS_NOT_AVAILABLE'])
    else:
        cursor, keys = redis_store.zscan(app.config['REDIS_NOT_AVAILABLE'], 0)
        keys = set([k[0] for k in keys])
        while cursor != 0:
            to_remove.extend(keys.intersection(available))
            not_available.difference_update(keys)
            cursor, keys = redis_store.zscan(app.config['REDIS_NOT_AVAILABLE'],
                    cursor)
            keys = set([k[0] for k in keys])
    if len(to_remove) > 0:
        redis_store.zrem(app.config['REDIS_NOT_AVAILABLE'], to_remove)
    if len(not_available) > 0:
        redis_store.zadd(app.config['REDIS_NOT_AVAILABLE'], **{k:0 for k in not_available})

@manager.command
def warm_up_redis():
    from flask import current_app
    import APITaxi_models as models
    from APITaxi.extensions import redis_store
    warm_up_redis_func(current_app, models.db, models.User, redis_store)
