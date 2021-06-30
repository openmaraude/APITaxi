import time

from flask import current_app
from geopy.distance import geodesic

from APITaxi_models2 import Station
from . import celery


TELEMETRY_TIMEOUT = 120


@celery.task(name='compute_waiting_taxis_stations')
def compute_waiting_taxis_stations():
    """If a taxi hasn't moved much since the last run, check if the position
    the driver is waiting at is a station.
    """
    now = int(time.time())
    max_time = now - TELEMETRY_TIMEOUT  # Only consider fresh telemetries
    current_app.logger.info('Run task compute_waiting_taxis_stations for telemetries older than %s', max_time)

    taxi_ids = []

    # Quickly select the taxis with fresh telemetry data
    pipeline = current_app.redis.pipeline()
    for taxi_operator in current_app.redis.zrangebyscore('timestamps', max_time, now):
        taxi_id, operator = taxi_operator.decode('utf8').split(':')
        pipeline.hget(f'taxi:{taxi_id}', operator)
        taxi_ids.append(taxi_id)

    current_app.logger.debug('Found %d taxis to check', len(taxi_ids))

    # Fetch their latest status and position
    telemetry_data = {}
    for taxi_id, telemetry in zip(taxi_ids, pipeline.execute()):
        if b' free ' not in telemetry:  # Fastpath
            current_app.logger.debug('Taxi %s is not free', taxi_id)
            continue
        _timestamp, lat, lon, status, _device, _version = telemetry.split()
        # Double check
        if status != b'free':
            current_app.logger.debug('Taxi %s is not free', taxi_id)
            continue
        telemetry_data[taxi_id] = {
            b'lat': lat,  # Keep the string representation for precision
            b'lon': lon,
        }

    # Fetch previous data from this subset of free taxis
    pipeline = current_app.redis.pipeline()
    for taxi_id in telemetry_data:  # Only the free taxis this time
        pipeline.hgetall(f'station:{taxi_id}')

    # Process to compare the current position with the last one recorded
    for taxi_id, previous_data in zip(telemetry_data, pipeline.execute()):
        current_app.logger.debug('Taxi %s previous_data %s', taxi_id, previous_data)
        telemetry = telemetry_data[taxi_id]
        station_id = ''  # Null value not accepted by Redis
        if previous_data:
            if now - int(previous_data[b'timestamp']) <= TELEMETRY_TIMEOUT:
                # Fast path if the position hasn't changed (should it happen in real life)
                if previous_data[b'station_id'] and telemetry[b'lat'] == previous_data[b'old_lat'] and telemetry[b'lon'] == previous_data[b'old_lon']:
                    current_app.logger.debug("Taxi %s hasn't moved from the station %s", taxi_id, previous_data[b'station_id'])
                    station_id = previous_data[b'station_id']
                else:
                    distance = geodesic(  # Or even great_circle if substantially faster?
                        (telemetry[b'lat'], telemetry[b'lon']),
                        (previous_data[b'old_lat'], previous_data[b'old_lon']),
                    )
                    print("distance", distance)
                    if distance.meters <= 50:
                        # TODO with a significant amount of taxis,
                        # test with preloading the stations in memory
                        wkt = b'POINT(%s %s)' % (telemetry[b'lon'], telemetry[b'lat'])
                        station = Station.find(wkt.decode())
                        print("station", station)
                        if station:
                            station_id = station.id
                            current_app.logger.debug('Taxi %s was found at station %s', taxi_id, station.id)
            else:
                current_app.logger.debug('Taxi %s telemetry is too old', taxi_id)
        else:
            # The first time, just store a new taxi
            current_app.logger.debug('Taxi %s has no previous station data', taxi_id)
        # Insert or update taxi data for the next time the task runs
        current_app.redis.hset(f'station:{taxi_id}', mapping={
            'timestamp': now,
            'old_lat': telemetry[b'lat'],
            'old_lon': telemetry[b'lon'],
            'station_id': station_id,
        })

    end = time.time()
    current_app.logger.info('Done computing taxis waiting in stations in %s', end - now)
