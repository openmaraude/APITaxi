import collections
import csv
import datetime
import json
import logging
import random

import click
from flask import Blueprint
from geopy.geocoders import Nominatim
import pyproj
from shapely.geometry import Point
from shapely.ops import transform
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from APITaxi_models2 import db, ADS, Station, Town, Taxi, Vehicle, VehicleDescription

from APITaxi2.views import geotaxi


blueprint = Blueprint('commands_debug_stations', __name__, cli_group=None)

logger = logging.getLogger(__name__)

now = datetime.datetime.now(datetime.timezone.utc).isoformat()


@blueprint.cli.command('fill_stations')
def fill_stations():
    # Build database of stations per town
    stations = collections.defaultdict(list)
    for station_id, lon, lat, insee in db.session.query(
        Station.id,
        func.ST_X(func.Geometry(Station.location)),
        func.ST_Y(func.Geometry(Station.location)),
        Town.insee,
    ).join(Town):
        stations[insee].append((station_id, lon, lat))

    # Move all free taxis to a station where available
    for taxi in db.session.query(Taxi).filter(
        ADS.insee.in_(stations),
        VehicleDescription.status == 'free',
    ).join(Vehicle, ADS).join(VehicleDescription).options(
        joinedload(Taxi.ads),
        joinedload(Taxi.added_by),
    ):
        station_id, lon, lat = random.choice(stations[taxi.ads.insee])
        print(f"Rerouting taxi {taxi.id} to station {station_id}")
        geotaxi._update_position([{
            'taxi_id': taxi.id,
            'lon': lon + random.uniform(-0.0001, 0.0001),  # ~15.7 m
            'lat': lat + random.uniform(-0.0001, 0.0001),  # ~15.7 m
        }], taxi.added_by)
