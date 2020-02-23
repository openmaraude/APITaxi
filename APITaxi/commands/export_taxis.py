#coding: utf-8
import APITaxi_models as models
from ..extensions import user_datastore
from ..descriptors import (ads as ads_descriptors,
        drivers as drivers_descriptors, vehicle as vehicle_descriptors)
from . import manager
from flask_login import login_user
from flask_restx import marshal
from flask import url_for, current_app
from tempfile import mkdtemp
import json, tarfile, os, requests
from io import StringIO


@manager.command
def export_taxis(filename='/tmp/taxis.tar.gz'):
    model_ads = ads_descriptors.ads_model
    model_driver = drivers_descriptors.driver_fields
    model_vehicle = vehicle_descriptors.vehicle_expect
    tar = tarfile.TarFile.open(filename, 'w:gz')
    users = set()

    for taxi in models.Taxi.query.all():
        if taxi.vehicle_id is None or taxi.ads_id is None or taxi.driver_id is None:
            continue
        vehicle = models.Vehicle.query.get(taxi.vehicle_id)
        for vehicle_description in models.VehicleDescription.query.filter_by(vehicle_id=vehicle.id).all():
            users.add(vehicle_description.added_by)
            login_user(user_datastore.get_user(vehicle_description.added_by))
            json_vehicle = json.dumps(marshal({"data":[vehicle]}, model_vehicle))
            tarinfo = tarfile.TarInfo('{}/vehicle_{}_{}.json'.format(taxi.id,
                vehicle.id,vehicle_description.added_by))
            tarinfo.size = len(json_vehicle)
            tar.addfile(tarinfo, StringIO.StringIO(json_vehicle))

        ads = models.ADS.query.get(taxi.ads_id)
        json_ads = json.dumps(marshal({"data":[ads]}, model_ads))
        tarinfo = tarfile.TarInfo('{}/ads.json'.format(taxi.id))
        tarinfo.size = len(json_ads)
        tar.addfile(tarinfo, StringIO.StringIO(json_ads))

        driver = models.Driver.query.get(taxi.driver_id)
        json_driver = json.dumps(marshal({"data":[driver]}, model_driver))
        tarinfo = tarfile.TarInfo('{}/driver.json'.format(taxi.id))
        tarinfo.size = len(json_driver)
        tar.addfile(tarinfo, StringIO.StringIO(json_driver))

    users_dict = dict()
    for user_id in users:
        user = user_datastore.get_user(user_id)
        users_dict[user_id] = user.email
    users_json = json.dumps(users_dict)
    tarinfo = tarfile.TarInfo('users.json')
    tarinfo.size = len(users_json)
    tar.addfile(tarinfo, StringIO.StringIO(users_json))

    tar.close()


@manager.command
def import_taxis(filename='/tmp/taxis.tar.gz'):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-VERSION": 2
    }

    pathname = mkdtemp()
    tar = tarfile.TarFile.open(filename, 'r:gz')
    tar.extractall(path=pathname)

    users_dict = None
    with open(os.path.join(pathname, 'users.json')) as f:
        users_dict = json.loads(f.read())

    users_apikey = dict([(id_, user_datastore.find_user(email=email).apikey)
        for (id_, email) in list(users_dict.items())])
    admin_apikey = None
    for user in user_datastore.user_model.query.all():
        if user.has_role('admin'):
            admin_apikey = user.apikey
            break

    dirs = [d for d in os.listdir(pathname) if os.path.isdir(os.path.join(pathname, d))]
    i = 1
    for d_name in dirs:
        dir_name = os.path.join(pathname, d_name)
        files = [f for f in os.listdir(dir_name)\
                if os.path.isfile(os.path.join(dir_name, f))]
        vehicles = [f for f in files if f.startswith('vehicle')]
        vehicle_id = None
        for vehicle in vehicles:
            user = vehicle.split('_')[2][:-len('.json')]
            headers['X-API-KEY'] = users_apikey[user]
            with open(os.path.join(dir_name, vehicle)) as f:
                r = requests.post(url_for('api.vehicle', _external=True),
                    headers=headers, data=f.read())
                vehicle_id = r.json()['data'][0]['id']
                licence_plate = r.json()['data'][0]['licence_plate']
                if r.status_code != 201:
                    current_app.logger.error(r.content)
                    current_app.logger(d_name)
                    current_app.logger('vehicle: {}'.format(f))
                    return

        with open(os.path.join(pathname, d_name, 'ads.json')) as f:
            ads = json.loads(f.read())
            ads['data'][0]['vehicle_id'] = vehicle_id

            r = requests.post(url_for('api.ads', _external=True),
                    headers=headers, data=json.dumps(ads))
            if r.status_code != 201:
                current_app.logger.error(r.content)
                current_app.logger.error(d_name)
                return

        with open(os.path.join(pathname, d_name, 'driver.json')) as f:
            driver = json.loads(f.read())
            r = requests.post(url_for('api.drivers', _external=True),
                    headers=headers, data=json.dumps(driver))
            if r.status_code != 201:
                current_app.logger.error(r.content)
                current_app.logger.error(d_name)
                return
        headers['X-API-KEY'] = admin_apikey
        r = requests.post(url_for('api.taxi_list', _external=True),
                headers=headers, data=json.dumps(
                    {"data": [
                        {
                            "ads": {
                                "insee": ads['data'][0]['insee'],
                                "numero": ads['data'][0]['numero']
                                },
                            "driver": {
                                "departement": driver['data'][0]['departement']['numero'],
                                "professional_licence": driver['data'][0]['professional_licence']
                                },
                            "vehicle": {
                                "licence_plate": licence_plate
                                },
                            "id": d_name,
                        }
                        ]}
                    ))
        if r.status_code != 201:
            current_app.logger.error(r.content)
            current_app.logger.error(d_name)
            return
        current_app.logger.info('Taxi {}/{} added'.format(i, len(dirs)))
        i += 1

