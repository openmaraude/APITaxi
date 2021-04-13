import collections
import csv
import datetime
import json
import logging

import click
from flask import Blueprint
from geopy.geocoders import Nominatim
import pyproj
from shapely.geometry import Point
from shapely.ops import transform

from APITaxi_models2 import db, Station, Town


blueprint = Blueprint('commands_stations', __name__, cli_group=None)

logger = logging.getLogger(__name__)

now = datetime.datetime.now(datetime.timezone.utc).isoformat()

wgs84 = pyproj.CRS('EPSG:4326')
lambert93 = pyproj.CRS('EPSG:2154')
projection = pyproj.Transformer.from_crs(lambert93, wgs84, always_xy=True).transform

geocoder = Nominatim(user_agent="le.taxi")


def _update_or_create(station_id, name, address, insee, places, lon, lat, call_number, info, mtime=None):
    if not lon or not lat:
        logger.warning('Ignoring station ID %s with missing coordinates', station_id)
        return None
    created = False
    station = db.session.query(Station).filter(Station.id == station_id).one_or_none()
    # Grenoble already using the station ID convention
    if not station:
        # Create
        station = Station(
            id=station_id,
            added_at=now)
        created = True
    # Update
    station.name = name.strip()
    station.address = address.strip()
    station.town = db.session.query(Town).filter(Town.insee == insee).one()  # Let it fail
    station.places = int(places or 0)
    station.location = f'POINT({lon} {lat})'
    # Normalize (use a python lib?)
    station.call_number = "".join(call_number.split()) if call_number else None
    station.info = info
    # HistoryMixin
    station.added_via = 'api'
    station.source = 'Ville'
    station.last_update_at = mtime or now
    db.session.add(station)
    return created


def import_grenoble_stations(csv_reader):
    counter = collections.Counter()
    for station_id, name, insee, address, places, call_number, lon, lat, info in csv_reader:
        # The Grenoble format is pretty much what we want
        counter[_update_or_create(station_id, name, address, insee, places, lon, lat, call_number, info)] += 1
    return counter


def import_paris_stations(csv_reader):
    counter = collections.Counter()
    for station_id, name, address, _postcode, call_number, _xlb93, _ylb93, _feature, point in csv_reader:
        # Normalize station ID to our convetion
        station_id = f'75006-T-{station_id}'
        lat, lon = point.split(',')
        counter[_update_or_create(station_id, name, address, '75056', 0, lon, lat, call_number, "")] += 1
    return counter


def import_rouen_stations(csv_reader):
    counter = collections.Counter()
    for station_id, name, insee, address, places, call_number, lon, lat, mtime in csv_reader:
        mtime = datetime.date(*map(int, reversed(mtime.split('/'))))
        counter[_update_or_create(station_id, name, address, insee, places, lon, lat, call_number, "", mtime)] += 1
    return counter


def import_antibes_stations(csv_reader):
    counter = collections.Counter()
    for commune, siret, numero, adresse, complement, lat, lon, mtime in csv_reader:
        station_id = f'06004-T-{numero}'
        if not numero:
            logger.warning('Ignoring station at %s with no identifier', adresse)
            counter[None] += 1
            continue
        mtime = datetime.date(*map(int, mtime.split('-')))
        counter[_update_or_create(station_id, complement or adresse, adresse, '06004', 0, lon, lat, None, "", mtime)] += 1
    return counter


def import_lyon_stations(data):
    counter = collections.Counter()
    for feature in data['features']:
        lon, lat = feature['geometry']['coordinates']
        props = feature['properties']
        station_id = f"69123-T-{props['gid']}"
        counter[_update_or_create(station_id, props['nom'], props['adresse'], '69123', props['nbemplacements'], lon, lat, None, "")] += 1
    return counter


def import_marseille_stations(csv_reader):
    counter = collections.Counter()
    for nom, type_site, adresse1, adresse2, code_postal, ville, contact, no_telephone, lon, lat, mtime in csv_reader:
        mtime = datetime.datetime.strptime(mtime, '%d/%m/%Y %H:%M:%S').date()
        station_id = f'13055-T-{lon[-3:]}'  # XXX
        counter[_update_or_create(station_id, nom, adresse1, '13055', 0, lon, lat, no_telephone or None, adresse2, mtime)] += 1
    return counter


def import_brest_stations(csv_reader):
    # This one is quite complicated...
    # We have the individual places, pick the first one, the others increment the number of places
    stations = {}
    for lon93, lat93, _, noarr, typearr, _, _, _, _, _, _, _, _, _, _, _, _, _, _, mtime in csv_reader:
        if typearr != 'STA_TAX':
            continue
        station_id = f'29019-T-{noarr}'
        if station_id in stations:
            stations[station_id][2] += 1
        else:
            lambert93_point = Point(float(lon93), float(lat93))
            wgs84_point = transform(projection, lambert93_point)
            lon, lat = wgs84_point.x, wgs84_point.y
            try:
                name, address = {
                    '8573': ("Prat Lédan", "Prat Lédan"),
                    '8608': ("Brest Arena", "Rue de Quélern"),
                    '9013': ("Gares", "Place du 19è RI"),
                    '9123': ("Patinoire", "Avenue de Tarente"),  # XXX
                    '9148': ("rue Kerfautras", "rue Kerfautras"),
                    '9302': ("Multiplexe Liberté", "Avancée Porte St Louis"),
                    '9303': ("Bas de Siam", "Bas de Siam"),
                    '9421': ("Rue Albert Rolland", "Rue Albert Rolland"),
                    '9543': ("Rue docteur Roux", "Rue docteur Roux"),
                    '9550': ("Recouvrance", "Rue Bouillon"),
                    '9797': ("Patinoire", "Avenue de Tarente"),
                    '9906': ("Place de Strasbourg", "Place de Strasbourg"),
                }[noarr]
            except KeyError:
                # Newer stations
                location = geocoder.reverse((lat, lon), exactly_one=True, language='fr-fr,fr')
                name = location.raw['address']['amenity']
                address = location.raw['address']['road']

            mtime = datetime.datetime.strptime(mtime, '%Y/%m/%d %H:%M:%S').date()
            stations[station_id] = [name, address, 1, lon, lat, mtime]

    counter = collections.Counter()
    for station_id, (name, address, places, lon, lat, mtime) in stations.items():
        counter[_update_or_create(station_id, name, address, '29019', places, lon, lat, None, "", mtime)] += 1
    return counter


PROVIDERS = {
    'grenoble': {
        'encoding': "Windows-1252",
        'importer': import_grenoble_stations,
    },
    'paris': {
        'encoding': "utf-8",
        'importer': import_paris_stations,
    },
    'le.taxi': {  # I forged the file in the Grenoble format
        'encoding': "utf-8",
        'importer': import_grenoble_stations,
    },
    'rouen': {  # I forged the file in the Grenoble format (plus mtime)
        'encoding': "utf-8",
        'importer': import_rouen_stations,
    },
    'brest': {
        'encoding': "utf-8",
        'importer': import_brest_stations,
    },
    # The following come from data.gouv.fr
    'antibes': {
        'encoding': "Windows-1252",
        'importer': import_antibes_stations,
    },
    'lyon': {
        'encoding': "utf-8",
        'importer': import_lyon_stations,
        'geojson': True,
    },
    'marseille': {
        'encoding': "utf-8",
        'importer': import_marseille_stations,
    }

}


def valid_provider(value):
    if value not in PROVIDERS:
        raise click.BadParameter('Provider %s is not supported' % value)
    return PROVIDERS[value]


@blueprint.cli.command('import_stations')
@click.argument('provider', required=True, type=valid_provider)
@click.argument('filename', required=True, type=click.Path(exists=True, dir_okay=False))
def import_stations(provider, filename):
    with open(filename, encoding=provider['encoding']) as handler:
        if provider.get('geojson'):
            reader = json.load(handler)
        else:
            sniffer = csv.Sniffer()
            sample = handler.read()
            dialect = sniffer.sniff(sample)
            handler.seek(0)
            reader = csv.reader(handler, dialect=dialect)
            if sniffer.has_header(sample):
                next(reader)

        counter = provider['importer'](reader)
        print(f'{counter[True]} stations created, {counter[False]} updated, {counter[None]} ignored.')

    db.session.commit()
