import os
import json
import time

import click
from flask import Blueprint, current_app
from geoalchemy2.shape import from_shape
from shapely.geometry import shape, MultiPolygon
import requests

from APITaxi2 import exclusions
from APITaxi_models2 import db, Exclusion


blueprint = Blueprint('commands_client', __name__, cli_group=None)

BASE_URL = "http://localhost:5000"  # "https://dev.api.taxi"


@blueprint.cli.command()
def client():
    session = requests.Session()
    session.headers.update({
        'X-Api-Key': os.environ['X_API_KEY'],
        'Content-Type':	'application/json',
    })
    lon, lat = 2.35, 48.86

    while True:
        lon_lat = input(f"\nlon lat ({lon} {lat}): ")
        if lon_lat:
            lon, lat = map(float, lon_lat.split())
        r = session.get(f'{BASE_URL}/taxis?lon={lon}&lat={lat}')
        if r.status_code != 200:
            print(r.status_code, r.json())
            continue
        data = r.json()['data']
        if not data:
            print("Aucun taxi")
            continue
        taxis = [taxi['id'] for taxi in data]
        for index, taxi in enumerate(taxis, start=1):
            print(f'{index}: {taxi}')
        index = input("\nTaxi ou r(eload) ? ")
        if index == 'r':
            continue
        taxi_id = taxis[int(index) - 1]
        break

    data = {
        "data": [
            {
            "customer_id": "abc123",
            "customer_lon": lon,
            "customer_lat": lat,
            "customer_address": "25 rue Quincampoix 75004 Paris",
            "customer_phone_number": "0678901234",
            "taxi_id": taxi_id,
            "operateur": "chauffeur professionnel"
            }
        ]
    }
    r = session.post(f'{BASE_URL}/hails', json=data)
    if r.status_code != 201:
        print(r.status_code, r.json())
        return
    hail = r.json()['data'][0]
    print("Demande de prise en charge", hail['id'])

    print("En attente de confirmation du chauffeur...")
    while True:  # 
        r = session.get(f"{BASE_URL}/hails/{hail['id']}")
        if r.status_code != 200:
            print(r.status_code, r.json())
            return
        hail = r.json()['data'][0]
        if hail['status'] not in ("received", "received_by_operator", "received_by_taxi"):
            break
        time.sleep(5)

    if hail['status'] == "accepted_by_taxi":
        print("Demande de prise en charge confirmée")
    else:
        print("Demande de prise en charge annulée")
        return

    status = None
    while not status:
        status = {
            'a': "accepted_by_customer",
            'd': "declined_by_customer"
        }.get(input("\na(ccept) or d(ecline)"))

    data = {
        "data": [
            {
                "status": status
            }
        ]
    }
    r = session.put(f"{BASE_URL}/hails/{hail['id']}", json=data)
    if r.status_code != 200:
        print(r.status_code, r.json())
        return
    hail = r.json()['data'][0]
    
    if hail['status'] == "accepted_by_customer":
        print("Le taxi est en approche, bonne route !")
    else:
        print("Course annulée")
