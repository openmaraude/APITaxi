# -*- coding: utf-8 -*-
from ..extensions import db
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
def load_zupc(zupc_path):

    with open(zupc_path) as f:
        for feature in json.load(f)['features']:
            wkb = shape.from_shape(geometry.shape(feature['geometry']))
            parent = ZUPC.query.filter_by(insee=feature['properties'][0]).first()
            for insee in feature['properties']:
                zupc = ZUPC.query.filter_by(insee=insee).first()
                if not zupc:
                    zupc = ZUPC()
                    zupc.insee = insee
                    zupc.departement = parent.departement
                    zupc.nom = parent.nom
                    db.session.add(zupc)
#This is the case in Paris and Lyon, but it's not important
                zupc.shape = wkb
                zupc.parent_id = parent.id
            db.session.commit()
