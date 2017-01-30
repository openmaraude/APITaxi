# -*- coding: utf-8 -*-
from APITaxi_models.taxis import ADS
import APITaxi_models as models
from . import manager
from sqlalchemy import distinct
from geoalchemy2 import shape
from shapely import geometry, ops
import json
from operator import itemgetter
from flask import current_app

@manager.command
def update_zupc():
    insee_list = map(itemgetter(0), current_app.extensions['sqlalchemy'].db\
            .session.query(distinct(ADS.insee)).all())
    for insee in insee_list:
        zupc = models.ZUPC.query.filter_by(insee=insee).order_by(
            models.ZUPC.id.desc()).first()
        for ads in ADS.query.filter_by(insee=insee).all():
            ads.zupc_id = zupc.id
    current_app.extensions['sqlalchemy'].db.session.commit()


def add_zupc(wkb, insee, parent):
    zupc = models.ZUPC.query.filter_by(insee=insee).first()
    if not zupc:
        zupc = models.ZUPC()
        zupc.insee = insee
        zupc.departement = parent.departement
        zupc.nom = parent.nom
        current_app.extensions['sqlalchemy'].db.session.add(zupc)
#This is the case in Paris and Lyon, but it's not important
    zupc.shape = wkb
    zupc.parent_id = parent.id
    current_app.extensions['sqlalchemy'].db.session.add(zupc)


@manager.command
def load_zupc(zupc_path):

    with open(zupc_path) as f:
        for feature in json.load(f)['features']:
            wkb = shape.from_shape(geometry.shape(feature['geometry']))
            properties = feature['properties']
            for p in properties:
                parent = models.ZUPC.query.filter_by(insee=p).first()
                if parent:
                    break
            if not parent:
                current_app.logger.error(
                    'Unable to get a insee code in : {}'.format(properties)
                )
                return
            for insee in properties:
                add_zupc(wkb, insee, parent)
            current_app.extensions['sqlalchemy'].db.session.commit()
    update_zupc()


@manager.command
def add_airport_zupc(zupc_file_path, insee):
    if isinstance(insee, str) or isinstance(insee, unicode):
        insee = [insee]
    with open(zupc_file_path) as f_zupc:
        geojson = json.load(f_zupc)
        if geojson['type'] == 'FeatureCollection':
            geojson = geojson['features'][0]
        wkb_airport = geometry.shape(geojson['geometry'])
        for i in insee:
            parent = models.ZUPC.query.filter_by(insee=i).first()
            if not parent:
                current_app.logger.error('Unable to find parent ZUPC: {}'.format(
                    i)
                )
            current_app.logger.info('Begin to compute union')
            l = [wkb_airport] + list(shape.to_shape(parent.shape).geoms)
            wkb = geometry.MultiPolygon([ops.cascaded_union(l)])
            current_app.logger.info('Finished to compute union')
            add_zupc(shape.from_shape(wkb), i + 'A', parent)
        current_app.extensions['sqlalchemy'].db.session.commit()

