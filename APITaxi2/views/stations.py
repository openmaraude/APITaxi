import collections
import csv
import datetime
import io
import json
import operator
import time

from flask import Blueprint, current_app
from flask_security import login_required, roles_accepted
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from APITaxi_models2 import db, Station


blueprint = Blueprint('stations', __name__)

# Properties common to the GeoJSON and CSV format
PROPERTIES = {
    'id': operator.attrgetter('id'),
    'nom': operator.attrgetter('name'),
    'insee': operator.attrgetter('town.insee'),
    'adresse': operator.attrgetter('address'),
    'emplacements': lambda station: station.places or "",  # Not 0
    'no_appel': operator.attrgetter('call_number'),
    'info': operator.attrgetter('info'),
}

# The CSV format doesn't have exactly the same columns
COLUMNS = ['id', 'nom', 'insee', 'geopoint', 'adresse', 'emplacements', 'no_appel', 'info']


# TODO 24h cache headers for the reverse proxy
@blueprint.route('/stations/stations.csv', methods=['GET'])
def stations_csv():
    """
    Exposing the stations under our public schema.

    This does not contain the real-time information about taxis in station.
    """
    t0 = time.time()
    stations = db.session.query(
        Station, func.ST_X(func.Geometry(Station.location)), func.ST_Y(func.Geometry(Station.location))
    ).options(
        joinedload(Station.town)
    ).order_by(Station.id)  # Will order by INSEE then local ID

    result = io.StringIO()
    writer = csv.writer(result, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)
    writer.writerow(COLUMNS)

    for station, xlong, ylat in stations:
        writer.writerow([
            f"{xlong}, {ylat}" if column == 'geopoint' else PROPERTIES[column](station)
            for column in COLUMNS
        ])

    t1 = time.time()
    current_app.logger.info("Generated stations CSV in %0.3f seconds", (t1 - t0))

    return result.getvalue(), 200, {
        'Content-Type': "text/plain; charset=utf-8",
        'Content-Disposition': datetime.datetime.now().strftime('"inline; filename="stationstaxi_LeTaxi_%Y%m%d.csv"')
    }


# TODO 24h cache headers for the reverse proxy
@blueprint.route('/stations/stations.json', methods=['GET'])
def stations_geojson():
    """
    Exposing the stations under our public schema.

    This does not contain the real-time information about taxis in station.
    """
    t0 = time.time()
    stations = db.session.query(
        Station, func.ST_AsGeoJSON(Station.location)
    ).options(
        joinedload(Station.town)
    ).order_by(Station.id)  # Will order by INSEE then local ID

    result = {
        'type': "FeatureCollection",
        'properties': {
            'version': "0.0.3",
            'date': datetime.date.today().isoformat(),
            'producteur': "le.taxi",
        },
        'features': [
            {
                'type': "Feature",
                'geometry': json.loads(geometry),
                'properties': {
                    prop: getter(station)
                    for prop, getter in PROPERTIES.items()
                    if getter(station)
                }
            } for station, geometry in stations
        ]
    }

    t1 = time.time()
    current_app.logger.info("Generated stations JSON in %0.3f seconds", (t1 - t0))

    return result, 200, {
        'Content-Type': "text/plain; charset=utf-8",
        'Content-Disposition': datetime.datetime.now().strftime('"inline; filename="stationstaxi_LeTaxi_%Y%m%d.json"')
    }


# TODO roles, and limit to stations in the same zone
@blueprint.route('/stations/live/', methods=['GET'])
@login_required
@roles_accepted('admin')
def stations_live():
    """
    Return the associative array between a station ID and the number of free taxis found
    waiting around this station.

    The "join" must be made with either the CSV or GeoJSON export above.
    """
    now = int(time.time())
    min_ = now - 2 * 60  # two minutes lifetime
    station_count = collections.Counter()
    for station_taxi in current_app.redis.zrangebyscore('stations_live', min_, now):
        station_id, _taxi_id = station_taxi.split(b':')
        station_id = station_id.decode()
        station_count[station_id] += 1

    end = time.time()
    current_app.logger.debug('generated station count in %f', (end - now))

    return {
        'timestamp': now,
        'stations': station_count,
        'total': sum(station_count.values())  # debug to remove
    }, 200
