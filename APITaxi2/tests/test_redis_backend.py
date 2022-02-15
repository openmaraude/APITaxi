import time


from APITaxi2 import redis_backend


def test_get_taxi(app):
    now = int(time.time())

    assert redis_backend.get_taxi('taxi_id', 'operator') is None

    app.redis.hset('taxi:taxi_id', 'operator', f'{now} 48.86 2.35 free phone 2')

    ret = redis_backend.get_taxi('taxi_id', 'operator')
    assert ret
    assert ret.timestamp == now
    assert ret.lat == 48.86
    assert ret.lon == 2.35
    assert ret.status == 'free'
    assert ret.device == 'phone'
    assert ret.version == 2


def test_get_timestamps_entries_between(app):
    now = int(time.time())
    app.redis.zadd('timestamps', {'taxi:operator': now})
    app.redis.zadd('timestamps', {'taxi2:operator2': now - 10})
    app.redis.zadd('timestamps', {'taxi3:operator3': now + 10})
    app.redis.zadd('timestamps', {'taxi4:operator4': now - 500})
    app.redis.zadd('timestamps', {'taxi5:operator5': now + 500})

    res = redis_backend.get_timestamps_entries_between(now - 100, now + 100)
    assert len(res) == 3
    assert {r.taxi_id for r in res} == {'taxi', 'taxi2', 'taxi3'}


def test_list_taxis(app):
    now = int(time.time())
    app.redis.hset('taxi:taxi1', 'operator1', f'{now} 48.86 2.35 free phone 2')
    app.redis.hset('taxi:taxi2', 'operator2', f'{now - 50} 48.86 2.35 free phone 2')
    app.redis.hset('taxi:taxi3', 'operator3', f'{now + 50} 48.86 2.35 free phone 2')
    app.redis.hset('taxi:taxi4', 'operator4', f'{now - 500} 48.86 2.35 free phone 2')
    app.redis.hset('taxi:taxi5', 'operator5', f'{now + 500} 48.86 2.35 free phone 2')

    res = redis_backend.list_taxis(now - 100, now + 100)
    assert len(res) == 3
    assert {r.taxi_id for r in res} == {'taxi1', 'taxi2', 'taxi3'}


def test_set_taxi_availability(app):
    # Not available, must be in ZSET not_available
    redis_backend.set_taxi_availability('taxi_id', 'operator', False)
    assert len(app.redis.zrange('not_available', 0, -1)) == 1

    # Not available, must be removed from ZSET not_available
    redis_backend.set_taxi_availability('taxi_id', 'operator', True)
    assert len(app.redis.zrange('not_available', 0, -1)) == 0


def test_taxis_locations_by_operator(app):
    now = int(time.time())
    app.redis.geoadd('geoindex_2', [2.35000, 48.86000, 'taxi1:operator1'])
    app.redis.zadd('timestamps', {'taxi1:operator1': now})

    app.redis.geoadd('geoindex_2', [2.35001, 48.86001, 'taxi1:operator2'])
    app.redis.zadd('timestamps', {'taxi1:operator2': now})

    app.redis.geoadd('geoindex_2', [2.35002, 48.86002, 'taxi2:operator3'])
    app.redis.zadd('timestamps', {'taxi2:operator3': now})

    # Outside of range
    app.redis.geoadd('geoindex_2', [2.3, 47, 'taxi3:operator4'])
    app.redis.zadd('timestamps', {'taxi3:operator4': now})

    res = redis_backend.taxis_locations_by_operator(2.35, 48.86, 500)
    assert len(res) == 2
    assert len(res['taxi1']) == 2
    assert len(res['taxi2']) == 1


def test_log_hail(app, moteur):
    redis_backend.log_hail(
        'hail_id', 'POST', {'data': 'xxx'}, 'received',
        request_user=moteur.user, response_payload={},
        response_status_code=200, hail_final_status='failure'
    )
    assert len(app.redis.zrange('hail:hail_id', 0, -1, withscores=True)) == 1
