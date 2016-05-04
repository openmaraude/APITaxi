#coding: utf-8
import urllib2, os, zipfile, shapefile, copy, glob
from . import manager
from shapely.geometry import shape, MultiPolygon
from APITaxi_models import db, administrative, taxis
from geoalchemy2.shape import from_shape
from geoalchemy2 import func
from itertools import groupby
from sqlalchemy.sql import select
from sqlalchemy import Table, Column, Boolean
from sqlalchemy.ext.automap import automap_base

def download_wanted(temp_dir):
    if os.path.isdir(temp_dir):
        in_ = raw_input("contours has already been downloaded, do you want to download it again ? [y/n]")
        if in_ == "n":
            return False
    else:
        os.mkdir(temp_dir)
    return True


def download_contours_file(temp_dir,
    url = "http://osm13.openstreetmap.fr/~cquest/openfla/export/communes-20160119-shp.zip"):
    file_name = url.split('/')[-1]
    u = urllib2.urlopen(url)
    full_file_name = os.path.join(temp_dir, file_name)
    f = open(full_file_name, 'wb')
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    print "Downloading: %s Bytes: %s" % (file_name, file_size)

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
        print status,
    f.close()

    with zipfile.ZipFile(full_file_name, "r") as z:
        z.extractall(temp_dir)

    return os.path.join(temp_dir, file_name.split(".")[0])


def create_temp_table(temp_table_name="zupc_temp"):
    table = Table(temp_table_name, db.metadata,
                  Column('multiple', Boolean(), default=False),
                  *[Column(c.name, c.type, autoincrement=c.autoincrement,
                           default=c.default, key=c.key, index=c.index,
                           nullable=c.nullable, primary_key=c.primary_key) 
                    for c in administrative.ZUPC.__table__.columns]
    )
    if table.exists(db.engine):
        table.drop(db.engine)
    table.create(db.engine)
    db.session.commit()
    db.Model.metadata.reflect(db.engine)
    Base = automap_base(metadata=db.metadata, declarative_base=db.Model)
    Base.prepare()
    return Base.classes[temp_table_name]


def records(filename):
    reader = shapefile.Reader(filename[:-4])
    fields = reader.fields[1:]
    field_names = [field[0] for field in fields]
    for sr in reader.iterShapeRecords():
        geom = sr.shape.__geo_interface__
        atr = dict(zip(field_names, sr.record))
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
            print "Unable to find departement for insee: {}".format(properties['insee'])
            continue
        z = zupc_obj()
        z.nom = properties['nom']
        z.insee = properties['insee']
        z.departement_id = departement.id
        z.shape = from_shape(MultiPolygon([shape(geom)]), srid=4326)
        z.active = False
        db.session.add(z)
        if (i%100) == 0:
            db.session.commit()
        i += 1
        status = r"%10d zupc ajoutées" % (i)
        status = status + chr(8)*(len(status)+1)
        print status,

    db.session.commit()
    print "%10d zupc ajoutées" %i


def union_zupc(filename, zupc_obj):
    with open(filename) as f:
        insee_list = map(lambda s: s.strip('\n'), f.readlines())

    parent_id = zupc_obj.query.with_entities(zupc_obj.id)\
            .filter_by(insee=insee_list[0]).first()
    if parent_id is None:
        return None
    if len(insee_list) == 1:
        return parent_id

    subquery = db.session.query(
        func.ST_Union(func.Geometry(zupc_obj.shape))).filter(
            zupc_obj.insee.in_(insee_list)
        )
    zupc_obj.query.filter(zupc_obj.insee.in_(insee_list)).update(
        {'shape': subquery.first()[0],
         'parent_id': parent_id
        }, synchronize_session='fetch'
    )
    query_string = "UPDATE {} SET multiple ='True' where insee in %s;".format(
        zupc_obj.__table__.name)
    cur = db.session.connection().connection.cursor()
    cur.execute(query_string, (tuple(insee_list),))
    db.session.commit()
    return parent_id


def load_include_geojson(parent_id, geojson_file, zupc_obj):
    return load_geojson(parent_id, geojson_file, zupc_obj, "union")


def load_exclude_geojson(parent_id, geojson_file, zupc_obj):
    return load_geojson(parent_id, geojson_file, zupc_obj, "difference")


def load_geojson(parent_id, geojson_file, zupc_obj, func_name):
    if parent_id is None:
        return None
    with open(geojson_file) as f:
        s = shape(json.load(f))
        parent_zupc = zupc_obj.query.get(parent_id)
        new_shape = getattr(s, func_name)(parent_zupc.shape)
        parent_zupc.update(
            {'shape': new_shape}
        )
        db.session.commit()

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
            db.session.add(z)
    db.session.commit()



def load_dir(dirname, zupc_obj):
    parent_id = None
    for f in glob.glob(os.path.join(dirname, '*.list')):
        parent_id = union_zupc(f, zupc_obj)
    for f in glob.glob(os.path.join(dirname, '*.include')):
        load_include_geojson(parent_id, f, zupc_obj)
    for f in glob.glob(os.path.join(dirname, '*.exclude')):
        load_include_geojson(parent_id, f, zupc_obj)
    for f in glob.glob(os.path.join(dirname, '*.arrondissements')):
        load_arrondissements(parent_id, f, zupc_obj)


def load_zupc(d, zupc_obj):
    for root, dirs, files in os.walk(d):
        for dir_ in dirs:
            print "Importing zupc {}".format(dir_)
            load_dir(os.path.join(d, dir_), zupc_obj)


def get_shape_filename(temp_dir):
    l = glob.glob(os.path.join(temp_dir, '*.shp'))
    if len(l) == 0:
        return None
    return l[0]

def confirm_zones():
    print "You can check zones on /zupc/_show_temp"
    in_ = raw_input("Do you want to confirm this zones ? (y/n)")
    return in_ == "y"

def merge_zones(temp_zupc_obj):
    print "Find unmergeable insee codes"
#Find unmergeable insee codes
    ZUPC = administrative.ZUPC
    insee_zupc = set([a.insee
          for a in db.session.query(taxis.ADS).distinct(taxis.ADS.insee).all()]
    )
    insee_temp = set([z.insee
                      for z in
                      db.session.query(temp_zupc_obj).distinct(temp_zupc_obj.insee).all()]
    )
    diff = insee_zupc.difference(insee_temp)
    if len(diff) > 0:
        print "These ZUPC can't be found in temp_zupc: {}".format(diff)
        return False
    last_zupc_id = db.session.execute('SELECT max(id) FROM "ZUPC"').fetchall()[0][0]
    print "Insert temp_zupc in ZUPC"
    db.session.execute("""INSERT INTO "ZUPC"
                       (departement_id, nom, insee, shape, active)
                       SELECT departement_id, nom, insee, shape, active FROM zupc_temp""")
    db.session.commit()

    zupc_with_parent = temp_zupc_obj.query.filter(
        temp_zupc_obj.parent_id != temp_zupc_obj.id).all()
    for parent_insee, zs in groupby(zupc_with_parent, lambda k: k.parent.insee):
        parent_id = ZUPC.query.filter(ZUPC_id > last_zupc_id)\
                .filter(ZUPC.insee==parent_insee).first().id
        for z in zs:
            z_to_update = ZUPC.query.filter(ZUPC.id > last_zupc_id)\
                .filter(ZUPC.insee==z.insee).first()
            z_to_update.parent_id = parent_id
            db.session.add(z_to_update)
    db.session.commit()
    print "Updating zupc_id in ADS"
    map_zupc_insee_id = {z.insee: z.id for z in ZUPC.query.filter(ZUPC.id > last_zupc_id).all()}
    print map_zupc_insee_id
    i = 0
    for ads in taxis.ADS.query.all():
        i += 1
        ads.zupc_id = map_zupc_insee_id[ads.insee]
        if i%100 == 0:
            db.session.commit()
            status = "Updated {} ADS".format(i)
            status = status + chr(8)*(len(status)+1)
            print status,
    db.session.commit()
    print "Removing old ZUPC"
    db.session.execute("""create table zupc_to_swap (
                       like "ZUPC" including defaults including constraints
                       including indexes);
                       INSERT INTO zupc_to_swap SELECT * FROM "ZUPC" WHERE id > {};
                       DROP TABLE IF EXISTS old_zupc;
                       ALTER TABLE "ZUPC" RENAME TO old_zupc;
                       ALTER TABLE zupc_to_swap RENAME TO "ZUPC";""".format(last_zupc_id))
    db.session.commit()

@manager.command
def import_zupc():
    temp_dir = '/tmp/temp_contours'
    wanted = download_wanted(temp_dir)
    if wanted:
        download_contours_file(temp_dir)

    shape_filename = get_shape_filename(temp_dir)
    if not shape_filename:
        print "No shapefile in {}".format(temp_dir)
        return

    z = create_temp_table()
    load_zupc_temp_table(shape_filename, z)
    load_zupc('/tmp/zupc', z)
    if not confirm_zones():
        return
    merge_zones(z)
