#coding: utf-8
import urllib2, os, zipfile, shapefile, copy, glob
from . import manager
from shapely.geometry import shape, MultiPolygon
from APITaxi_models import db, administrative
from geoalchemy2.shape import from_shape
from geoalchemy2 import func

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
    zupc_temp = copy.deepcopy(administrative.ZUPC)
    zupc_temp.__table__.name = temp_table_name
    if zupc_temp.__table__.exists(db.engine):
        zupc_temp.__table__.drop(db.engine)
    zupc_temp.__table__.create(db.engine)
    db.session.commit()
    db.engine.execute('ALTER TABLE "%s" ADD COLUMN multiple boolean' % 
                      (temp_table_name)
    )
    db.engine.execute('ALTER TABLE "%s" ALTER COLUMN multiple SET DEFAULT False' %
                     (temp_table_name)
    )
    return zupc_temp


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
        db.session.add(z)
        if (i%100) == 0:
            db.session.commit()
        i += 1
        status = r"%10d zupc ajoutées" % (i)
        status = status + chr(8)*(len(status)+1)
        print status,

    db.session.commit()


def union_zupc(filename, zupc_obj):
    with open(filename) as f:
        insee_list = map(lambda s: s.strip('\n'), f.readlines())

    parent_id = zupc_obj.query.with_entities(zupc_obj.id)\
            .filter_by(insee=insee_list[0]).first()
    if parent_id is None:
        return None

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


def load_dir(dirname, zupc_obj):
    parent_id = None
    for f in glob.glob(os.path.join(dirname, '*.list')):
        parent_id = union_zupc(f, zupc_obj)
    for f in glob.glob(os.path.join(dirname, '*.include')):
        load_include_geojson(parent_id, f, zupc_obj)
    for f in glob.glob(os.path.join(dirname, '*.exclude')):
        load_include_geojson(parent_id, f, zupc_obj)


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
