import collections
import csv
import datetime
import functools
import io
import json
import operator
import time

from flask import Blueprint, current_app, Response
from flask_security import login_required, roles_accepted
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from APITaxi2 import schemas
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


@blueprint.route('/stations/all', methods=['GET'])
def stations_all():
    """
    Endpoint for the console
    """
    stations = db.session.query(
        Station.id,
        Station.name,
        Station.places,
        func.ST_AsGeoJSON(Station.location),
    )

    schema = schemas.DataStationSchema()
    return schema.dump({
        'data': [{
            'id': id,
            'name': name,
            'places': places,
            'geojson': json.loads(geojson),
        } for (id, name, places, geojson) in stations
    ]})


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

    now = datetime.datetime.now()
    then = now + datetime.timedelta(hours=24)

    return result.getvalue(), 200, {
        'Content-Type': "text/plain; charset=utf-8",
        'Content-Disposition': now.strftime('"inline; filename="stationstaxi_LeTaxi_%Y%m%d.csv"'),
        'Expires': then.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        'Cache-Control': 'public,max-age=%d' % (then - now).total_seconds(),
    }


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

    now = datetime.datetime.now()
    then = now + datetime.timedelta(hours=24)

    return result, 200, {
        'Content-Type': "text/plain; charset=utf-8",
        'Content-Disposition': datetime.datetime.now().strftime('"inline; filename="stationstaxi_LeTaxi_%Y%m%d.json"'),
        'Expires': then.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        'Cache-Control': 'public,max-age=%d' % (then - now).total_seconds(),
    }
