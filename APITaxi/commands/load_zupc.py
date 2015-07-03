# -*- coding: utf-8 -*-
from .. import user_datastore
from ..models import db
from ..models.administrative import ZUPC, Departement
from flask.ext.script import prompt_pass
from validate_email import validate_email
from . import manager
from sqlalchemy import create_engine, Table, Column, String, Integer, MetaData
import glob, os, csv, sqlalchemy
from geoalchemy2 import shape
from shapely import geometry, wkt
import json


@manager.command
def load_zupc(cs_zupc, zupc_path):
    departements = {}
    for departement in Departement.query.all():
        departements[departement.numero] = departement

    engine = sqlalchemy.create_engine(cs_zupc)
    i = 0
    for row in engine.execute('SELECT nom, insee, st_asewkt(geom) FROM zupc'):
        zupc = ZUPC()
        zupc.nom = row[0]
        zupc.insee = row[1]
        zupc.shape = shape.from_shape(wkt.loads(row[2]))
        departement = zupc.insee[:2] if zupc.insee[:2] != '97' else zupc.insee[:3]
        zupc.departement_id = departements[departement].id
        db.session.add(zupc)
        if i % 100 == 0:
            db.session.commit()
        i += 1
    db.session.commit()

    with open(zupc_path) as f:
        for feature in json.load(f)['features']:
            wkb = shape.from_shape(geometry.shape(feature['geometry']))
            parent = ZUPC.query.filter_by(insee=feature['properties'][0]).first()
            for insee in feature['properties']:
                zupc = ZUPC.query.filter_by(insee=insee).first()
                if not zupc:
#This is the case in Paris and Lyon, but it's not important
                    continue
                zupc.shape = wkb
                zupc.parent_id = parent.id
            db.session.commit()
