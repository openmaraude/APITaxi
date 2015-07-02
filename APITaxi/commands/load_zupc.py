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
from shapely import geometry
import json


@manager.command
def load_zupc(cs_zupc, zupc_path):
    #departements = {}
    #for departement in Departement.query.all():
    #    departements[departement.numero] = departement

    #engine = sqlalchemy.create_engine(cs_zupc)
    #i = 0
    #for row in engine.execute('SELECT nom, insee, st_asewkt(geom) FROM zupc'):
    #    zupc = ZUPC()
    #    zupc.nom = row[0]
    #    zupc.insee = row[1]
    #    zupc.shape = shape.from_shape(shapely.wkt.loads(row[2]))
    #    departement = zupc.insee[:2] if zupc.insee[:2] != '97' else zupc.insee[:3]
    #    zupc.departement_id = departements[departement].id
    #    db.session.add(zupc)
    #    if i % 100 == 0:
    #        db.session.commit()
    #    i += 1
    #db.session.commit()
    #print "{} shapes added, now inserting ZUPC".format(i)

    #print os.path.join(zupc_path, '*/*.zupc')
    for fzupc in glob.iglob(os.path.join(zupc_path, '*/*.zupc')):
        print fzupc
        dir_, fname = os.path.split(fzupc)
        fname, _ = os.path.splitext(fname)
        fwkb = os.path.join(dir_, fname + '.geojson')
        list_insee_codes = []
        with open(fzupc, 'rb') as f:
            for row in csv.reader(f, delimiter=','):
                list_insee_codes.append(row[2].strip())
        parent = ZUPC.query.filter_by(insee=list_insee_codes[0]).first()

        with open(fwkb) as f:
            wkb = shape.from_shape(geometry.shape(json.load(f)))
        for insee in list_insee_codes:
            print insee
            zupc = ZUPC.query.filter_by(insee=insee).first()
            zupc.shape = wkb
            zupc.parent_id = parent.id
            print zupc.id
        db.session.commit()
            

