#coding: utf-8
import urllib.request, urllib.error, urllib.parse, os, zipfile, shapefile, copy, glob
from . import manager
from shapely.geometry import shape, MultiPolygon
from shapely.ops import cascaded_union as union
from shapely import wkt
import APITaxi_models as models
from geoalchemy2.shape import from_shape, to_shape
from geoalchemy2 import func
from itertools import groupby
from sqlalchemy.sql import select
from sqlalchemy import Table, Column, Boolean
from sqlalchemy.ext.automap import automap_base
import json, sys

def download_wanted(temp_dir):
    if os.path.isdir(temp_dir):
        in_ = input("contours has already been downloaded, do you want to download it again ? [y/n]")
        if in_ == "n":
            return False
    else:
        os.mkdir(temp_dir)
    return True


def download_contours_file(temp_dir,
    url = "http://osm13.openstreetmap.fr/~cquest/openfla/export/communes-20160119-shp.zip"):
    file_name = url.split('/')[-1]
    u = urllib.request.urlopen(url)
    full_file_name = os.path.join(temp_dir, file_name)
    f = open(full_file_name, 'wb')
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    print("Downloading: %s Bytes: %s" % (file_name, file_size))

    file_size_dl = 0
    block_sz = 8192
    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
        status = status + chr(8)*(len(status)+1)
        print(status)
    f.close()

    with zipfile.ZipFile(full_file_name, "r") as z:
        z.extractall(temp_dir)

    return os.path.join(temp_dir, file_name.split(".")[0])


def create_temp_table(temp_table_name="zupc_temp"):
    table = Table(temp_table_name, models.db.metadata,
                  Column('multiple', Boolean(), default=False),
                  *[Column(c.name, c.type, autoincrement=c.autoincrement,
                           default=c.default, key=c.key, index=c.index,
                           nullable=c.nullable, primary_key=c.primary_key) 
                    for c in models.ZUPC.__table__.columns]
    )
    if table.exists(models.db.engine):
        table.drop(models.db.engine)
    table.create(models.db.engine)
    models.db.session.commit()
    models.db.Model.metadata.reflect(models.db.engine)
    Base = automap_base(metadata=models.db.metadata, declarative_base=models.db.Model)
    Base.prepare()
    return Base.classes[temp_table_name]


def records(filename):
    reader = shapefile.Reader(filename[:-4])
    fields = reader.fields[1:]
    field_names = [field[0] for field in fields]
    for sr in reader.iterShapeRecords():
        geom = sr.shape.__geo_interface__
        atr = dict(list(zip(field_names, sr.record)))
        yield geom, atr


def load_zupc_temp_table(shape_filename, zupc_obj=None):
    departements = {
        d.numero: d for d in administrative.Departement.query.all()
    }


    def find_departement(p):
        for i in range(0, len(p['insee'])):
            if p['insee'][:i] in departements:
                return departements[p['insee'][:i]]
        return None

    i = 0

    for geom, properties in records(shape_filename):
        departement = find_departement(properties)
        if not departement:
            print("Unable to find departement for insee: {}".format(properties['insee']))
            continue
        z = zupc_obj()
        z.nom = properties['nom']
        z.insee = properties['insee']
        z.departement_id = departement.id
        z.shape = from_shape(MultiPolygon([shape(geom)]), srid=4326)
        z.active = False
        models.db.session.add(z)
        if (i%100) == 0:
            models.db.session.commit()
        i += 1
        status = r"%10d zupc ajoutées" % (i)
        status = status + chr(8)*(len(status)+1)
        print(status)

    models.db.session.commit()
    print("%10d zupc ajoutées" %i)


def union_zupc(filename, zupc_obj):
    with open(filename) as f:
        insee_list = [s.strip('\n') for s in f.readlines()]

    parent_id = zupc_obj.query.with_entities(zupc_obj.id)\
            .filter_by(insee=insee_list[0]).first()
    if parent_id is None:
        return None
    if len(insee_list) == 1:
        return parent_id

    subquery = models.db.session.query(
        func.st_AsText(func.Geography(func.st_Multi(func.ST_Union(func.Geometry(zupc_obj.shape)))))).filter(
            zupc_obj.insee.in_(insee_list)
    )
    zupc_obj.query.filter(zupc_obj.insee.in_(insee_list)).update(
        {'shape': subquery.first()[0],
         'parent_id': parent_id
        }, synchronize_session='fetch'
    )
    zupc_obj.query.filter(zupc_obj.insee.in_(insee_list)).update({"multiple": True}, synchronize_session='fetch')
    models.db.session.commit()
    return parent_id


def load_include_geojson(parent_id, geojson_file, zupc_obj):
    return load_geojson(parent_id, geojson_file, zupc_obj, "union")


def load_exclude_geojson(parent_id, geojson_file, zupc_obj):
    return load_geojson(parent_id, geojson_file, zupc_obj, "difference")


def load_geojson(parent_id, geojson_file, zupc_obj, func_name):
    if parent_id is None:
        return None
    with open(geojson_file) as f:
        jdata = json.load(f)
        if 'features' in jdata:
            if len(jdata['features']) == 1:
                s = shape(jdata['features'][0]['geometry'])
            else:
                s = union([shape(f['geometry']) for f in jdata['features']])
        else:
            s = shape(jdata['geometry'])
        parent_zupc = zupc_obj.query.get(parent_id)
        parent_shape = to_shape(parent_zupc.shape)
        new_shape = MultiPolygon([getattr(s, func_name)(parent_shape)])
        parent_zupc.query.filter(id==parent_id).update(
            {'shape': wkt.dumps(new_shape)}
        )
        models.db.session.commit()

def load_arrondissements(parent_id, arrondissements_file, zupc_obj):
    if parent_id is None:
        return
    parent_zupc = zupc_obj.query.get(parent_id)
    with open(arrondissements_file) as f:
        for insee in f.readlines():
            insee = insee.strip()
            if not insee:
                continue
            z = zupc_obj()
            for att in ['departement_id', 'nom', 'shape']:
                setattr(z, att, getattr(parent_zupc, att))
            z.insee = insee
            z.active = False
            models.db.session.add(z)
    models.db.session.commit()


def override_name(parent_id, special_name_list, zupc_obj):
    if parent_id is None:
        return
    parent_zupc = zupc_obj.query.get(parent_id)
    for special_name in special_name_list:
        with open(special_name) as f:
            line = f.readline().decode('utf-8')
            delimiter = ' ' if ' ' in line else ','
            name, insee = [s.strip() for s in line.split(delimiter)]

            parent_zupc.name = name
            parent_zupc.insee = insee
            models.db.session.add(parent_zupc)
    models.db.session.commit()


def load_dir(dirname, zupc_obj):
    parent_id = None
    for f in glob.glob(os.path.join(dirname, '*.list')):
        parent_id = union_zupc(f, zupc_obj)
    special_name_insee = glob.glob(os.path.join(dirname, 'special_name_insee'))
    if len(special_name_insee) == 1:
        override_name(parent_id, special_name_insee, zupc_obj)
    for f in glob.glob(os.path.join(dirname, '*.include')):
        load_include_geojson(parent_id, f, zupc_obj)
    for f in glob.glob(os.path.join(dirname, '*.exclude')):
        load_include_geojson(parent_id, f, zupc_obj)
    for f in glob.glob(os.path.join(dirname, '*.arrondissements')):
        load_arrondissements(parent_id, f, zupc_obj)


def load_zupc(d, zupc_obj):
    for root, dirs, files in os.walk(d):
        for dir_ in dirs:
            print(str("Importing zupc {}").format(str(dir_)))
            load_dir(os.path.join(d, dir_), zupc_obj)


def get_shape_filename(temp_dir):
    l = glob.glob(os.path.join(temp_dir, '*.shp'))
    if len(l) == 0:
        return None
    return l[0]

def confirm_zones():
    print("You can check zones on /zupc/_show_temp")
    in_ = input("Do you want to confirm this zones ? (y/n)")
    return in_ == "y"

def merge_zones(temp_zupc_obj):
    print("Find unmergeable insee codes")
#Find unmergeable insee codes
    ZUPC = models.ZUPC
    insee_zupc = set([a.insee
          for a in models.db.session.query(models.ADS).distinct(models.ADS.insee).all()]
    )
    insee_temp = set([z.insee
                      for z in
                      models.db.session.query(temp_zupc_obj).distinct(temp_zupc_obj.insee).all()]
    )
    diff = insee_zupc.difference(insee_temp)
    if len(diff) > 0:
        print("These ZUPC can't be found in temp_zupc: {}".format(diff))
        return False
    last_zupc_id = models.db.session.execute('SELECT max(id) FROM "ZUPC"').fetchall()[0][0]
    print("Insert temp_zupc in ZUPC")
    models.db.session.execute("""INSERT INTO "ZUPC"
                       (departement_id, nom, insee, shape, active)
                       SELECT departement_id, nom, insee, shape, active FROM zupc_temp""")
    models.db.session.commit()

    print("Updating parent_id in ZUPC")
    zupc_with_parent = temp_zupc_obj.query.filter(
        temp_zupc_obj.parent_id != temp_zupc_obj.id).all()
    for parent_insee, zs in groupby(zupc_with_parent, lambda k: k.parent.insee):
        parent_id = ZUPC.query.filter(ZUPC_id > last_zupc_id)\
                .filter(ZUPC.insee==parent_insee).first().id
        for z in zs:
            z_to_update = ZUPC.query.filter(ZUPC.id > last_zupc_id)\
                .filter(ZUPC.insee==z.insee).first()
            z_to_update.parent_id = parent_id
            models.db.session.add(z_to_update)
    models.db.session.commit()
    print("Updating zupc_id in ADS")
    map_zupc_insee_id = {z.insee: z.id for z in ZUPC.query.filter(ZUPC.id > last_zupc_id).all()}
    i = 0
    for ads in models.ADS.query.all():
        i += 1
        ads.zupc_id = map_zupc_insee_id[ads.insee]
        if i%100 == 0:
            models.db.session.commit()
            status = "Updated {} ADS".format(i)
            status = status + chr(8)*(len(status)+1)
            print(status)
    models.db.session.commit()
    print("Removing old ZUPC")
    models.db.session.execute("""create table zupc_to_swap (
                       like "ZUPC" including defaults including constraints
                       including indexes);
                       INSERT INTO zupc_to_swap SELECT * FROM "ZUPC" WHERE id > {};
                       DROP TABLE IF EXISTS old_zupc;
                       ALTER TABLE "ZUPC" RENAME TO old_zupc;
                       ALTER TABLE zupc_to_swap RENAME TO "ZUPC";""".format(last_zupc_id))
    models.db.session.commit()

@manager.command
def import_zupc(zupc_dir='/tmp/zupc', contours_dir='/tmp/temp_contours'):
    temp_dir = contours_dir
    wanted = download_wanted(temp_dir)
    if wanted:
        download_contours_file(temp_dir)

    shape_filename = get_shape_filename(temp_dir)
    if not shape_filename:
        print("No shapefile in {}".format(temp_dir))
        return

    z = create_temp_table()
    load_zupc_temp_table(shape_filename, z)
    load_zupc(zupc_dir, z)
    if not confirm_zones():
        return
    merge_zones(z)
