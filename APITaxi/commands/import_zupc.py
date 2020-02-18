# -*- coding: utf-8 -*-

import csv
import glob
import json
import logging
import os
import requests
import sys
from urllib.parse import urlparse
import zipfile

from geoalchemy2 import Geography
from geoalchemy2.shape import from_shape, to_shape
from shapely import wkt
from shapely.geometry import shape, MultiPolygon
from shapely.ops import cascaded_union
from sqlalchemy import Column, func
from sqlalchemy.orm.exc import NoResultFound
import shapefile

from APITaxi_models import db, Departement, ADS, ZUPC

from . import manager


logger = logging.getLogger(__name__)


# Archive downloaded and extracted to CONTOURS_DIR
CONTOURS_DEFAULT_URL = "http://osm13.openstreetmap.fr/~cquest/openfla/export/communes-20190101-shp.zip"

# Archive downloaded and extrated to ARRONDISSEMENTS_DIR
ARRONDISSEMENTS_DEFAULT_URL = "http://osm13.openstreetmap.fr/~cquest/openfla/export/arrondissements_municipaux-20180711-shp.zip"

# Temporary path where CONTOURS_URL is downloaded
CONTOURS_DEFAULT_TMPDIR = '/tmp/temp_contours'

# Temporary path where ARRONDISSEMENTS_URL is downloaded
ARRONDISSEMENTS_DEFAULT_TMPDIR = '/tmp/temp_arrondissements'
# Directory where https://github.com/openmaraude/ZUPC has been cloned
ZUPC_DEFAULT_DIRECTORY = '/tmp/ZUPC'

# Environment variable value considered as true
TRUE_VARS = ('1', 'y', 'yes')


def download_zipfile(url, download_path):
    """Download and extract ZIP file from `url` to `download_path`.
    """
    filename = os.path.basename(urlparse(url).path)
    fullpath = os.path.join(download_path, filename)

    download = True

    if os.path.exists(fullpath):
        ok = input("%s has already been downloaded, do you want to download it again ? [y/n]" % filename)
        download = ok.lower() in TRUE_VARS
    else:
        os.makedirs(download_path)

    if download:
        logger.info('Download %s to %s', url, fullpath)
        r = requests.get(url)
        with open(fullpath, 'wb') as handle:
            handle.write(r.content)

    with zipfile.ZipFile(fullpath) as archive:
        logger.info('Extract %s to %s', fullpath, download_path)
        archive.extractall(download_path)


def find_files_by_extension(path, extension):
    """Get the list of files with `extension` from `path`.
    """
    for name in os.listdir(path):
        if name.endswith('.' + extension):
            yield os.path.join(path, name)


def get_records_from_shapefile(shape_filename):
    """Yield records from `shape_filename`.
    """
    reader = shapefile.Reader(shape_filename)

    for shape_record in reader:
        feature = shape_record.__geo_interface__
        yield feature['geometry'], feature['properties']


def get_departement_from_INSEE(departements, insee_code):
    """Get the departement code from the INSEE code.

    `departements` is a dictionary where keys are the "numero" of the departement, and values the object in database.

    XXX: this function is not working for all cases, as departements and INSEE code might be completely different. For
    example, Saint-Pierre-Laval has the "code postal" 42620 but INSEE code 03250.
    """
    for i in range(len(insee_code)):
        if insee_code[:i] in departements:
            return departements[insee_code[:i]]


class ZUPC_tmp(db.Model):

    __tablename__ = 'zupc_temp'

    id = Column(db.Integer, primary_key=True)
    departement_id = Column(db.Integer, db.ForeignKey('departement.id'))
    nom = Column(db.String(255))
    insee = Column(db.String(), nullable=True)
    shape = Column(Geography(geometry_type='MULTIPOLYGON', srid=4326, spatial_index=False))
    parent_id = Column(db.Integer, db.ForeignKey('zupc_temp.id'))
    parent = db.relationship('ZUPC_tmp', remote_side=[id], lazy='joined')

    multiple = Column(db.Boolean, server_default='false')


def recreate_zupc_tmp_table():
    table = ZUPC_tmp.__table__

    if table.exists(db.engine):
        logger.info('Drop temporary table %s' % table.name)
        table.drop(db.engine)
    logger.info('Create temporary table %s' % table.name)
    table.create(db.engine)
    db.session.flush()

def fill_zupc_tmp_table_from_contours(shape_filename):
    """Build ZUPC temporary table. Rows only contain data from the contours database and need to be "completed" with
    data from the ZUPC repository.
    """
    departements = {
        departement.numero: departement
        for departement in Departement.query.all()
    }

    for geom, properties in get_records_from_shapefile(shape_filename):
        departement = get_departement_from_INSEE(departements, properties['insee'])
        if not departement:
            logger.warning('Unable to find departement of INSEE code %s', properties['insee'])
            continue

        obj = ZUPC_tmp(
            nom=properties['nom'],
            insee=properties['insee'],
            departement_id=departement.id,
            # 4326 is a reference to https://spatialreference.org/ref/epsg/wgs-84/
            shape=from_shape(MultiPolygon([shape(geom)]), srid=4326)
        )

        db.session.add(obj)

    db.session.commit()


def fill_zupc_union(filename):
    """zupc_temp table contains one row per INSEE code. In reality, one ZUPC can cover several INSEE codes. For example,
    the ZUPC of Paris cover the INSEE codes 75056, 92002, 92004, 93..., 94...

    The file "insee.list" from the ZUPC repository (eg. ZUPC/75_Paris/insee.list) contains this list of INSEE codes
    covered by each ZUPC. This function reads the file "insee.list" and:

    - if there is only one INSEE code covered by the ZUPC, return the ZUPC object
    - if there are several, update the shape of all the ZUPC entries to cover all INSEE codes, and set their parent
      to the first ZUPC of the list.

    This behavior is to keep backward compatibility where one "real" ZUPC is represented by several entries in database.
    We should instead probably store one ZUPC entry per "real" ZUPC, related to one or several INSEE codes.
    """
    with open(filename) as handle:
        insee_codes = handle.read().split()

    try:
        parent = ZUPC_tmp.query.filter_by(insee=insee_codes[0]).one()
    # Can happen in the case the referenced INSEE code has been previously "renamed" in "special_name_insee".
    except NoResultFound:
        logger.error('File %s references ZUPC %s which does not exist', filename, insee_codes[0])
        return None

    if len(insee_codes) == 1:
        return parent

    shape = db.session.query(
        func.st_AsText(func.Geography(func.st_Multi(func.ST_Union(func.Geometry(ZUPC_tmp.shape))))).label('shape')
    ).filter(ZUPC_tmp.insee.in_(insee_codes)).one()

    ZUPC_tmp.query.filter(ZUPC_tmp.insee.in_(insee_codes)).update({
        'shape': shape,
        'parent_id': parent.id,
        'multiple': True
    }, synchronize_session='fetch')
    db.session.flush()

    return parent


def fill_zupc_special_name(filename, parent_zupc):
    """Fill "special_name_insee" from the ZUPC repository can be used to override the name and INSEE code of a ZUPC.
    """
    with open(filename) as handle:
        lines = list(csv.reader(handle))

    if len(lines) != 1:
        raise ValueError('CSV file %s should contain exactly one line' % filename)
    insee, nom = lines[0]
    zupc = ZUPC_tmp(
        nom=nom,
        insee=insee,
        departement_id=parent_zupc.departement_id,
        # 4326 is a reference to https://spatialreference.org/ref/epsg/wgs-84/
        shape=parent_zupc.shape
    )
    db.session.add(zupc)
    db.session.flush()


def fill_zupc_update_shape(filename, parent_zupc, action):
    """Update shape of `parent_zupc` with the shapes defined in `filename`. `action` is a string that is either
    'include' or 'exclude'.

    If 'include', shapes of `filename` are added to `parent_zupc.shape`.
    If 'exclude', shapes of `filename` are removed from`parent_zupc.shape`.
    """
    assert action in ('include', 'exclude')

    with open(filename) as handle:
        data = json.load(handle)

    if data['type'] not in ('Feature', 'FeatureCollection'):
        raise ValueError('Unable to handle geojson type %s in %s' % (data['type'], filename))

    all_shapes = []
    if data['type'] == 'Feature':  # only one shape
        all_shapes = [shape(data['geometry'])]
    else:  # FeatureCollection: list of shapes
        all_shapes = [shape(part['geometry']) for part in data['features']]

    # new_shape = covering all polygons of all_shapes
    new_shape = cascaded_union(all_shapes)

    if action == 'include':
        update = new_shape.union(to_shape(parent_zupc.shape))
    else:
        update = new_shape.difference(to_shape(parent_zupc.shape))

    parent_zupc.shape = wkt.dumps(MultiPolygon([update]))

    # wkt.dumps returns a string, refreshing the session fetches the object from database to render parent_zupc.shape as
    # a geoalchemy2.elements.WKBElement.
    db.session.refresh(parent_zupc)

    db.session.add(parent_zupc)
    db.session.flush()


def fill_zupc(zupc_dir):
    """Insert informations into zupc_temp table.
    """
    logger.debug('Fill ZUPC temporary table with %s', zupc_dir)

    insee_list_filename = os.path.join(zupc_dir, 'insee.list')
    if not os.path.exists(insee_list_filename):
        logger.debug('No insee.list file in %s, nothing to do', zupc_dir)
        return

    parent_zupc = fill_zupc_union(insee_list_filename)
    if not parent_zupc:
        return

    special_name_filename = os.path.join(zupc_dir, 'special_name_insee')
    if os.path.exists(special_name_filename):
        fill_zupc_special_name(special_name_filename, parent_zupc)

    for filename in glob.glob(os.path.join(zupc_dir, '*.include')):
        fill_zupc_update_shape(filename, parent_zupc, 'include')

    for filename in glob.glob(os.path.join(zupc_dir, '*.exclude')):
        fill_zupc_update_shape(filename, parent_zupc, 'exclude')

    db.session.commit()


def fill_zupc_tmp_table_from_arretes(zupc_repo):
    """Fill informations in ZUPC tmp table from "arrêtés" stored in --zupc_repo.

    Each folder in the root directory of the ZUPC repository contains the files describing a ZUPC.
    """
    for zupc_dir in os.listdir(zupc_repo):
        fullpath = os.path.join(zupc_repo, zupc_dir)

        # Skip hidden directories and extra files
        if zupc_dir.startswith('.') or os.path.isfile(fullpath):
            continue

        fill_zupc(fullpath)


def fill_arrondissements(arrondissements_shape_filename):
    for geom, properties in get_records_from_shapefile(arrondissements_shape_filename):
        arrondissement_shape = from_shape(MultiPolygon([shape(geom)]), srid=4326)
        parent_zupc = db.session.query(ZUPC_tmp).filter(
                ZUPC_tmp.shape.ST_Intersects(arrondissement_shape)
            ).order_by(func.ST_Area(func.ST_Intersection(ZUPC_tmp.shape, arrondissement_shape)).desc()).first()
        multipolygon = shape(geom) if geom['type'] == 'MultiPolygon' else MultiPolygon([shape(geom)])
        obj = ZUPC_tmp(
            nom=properties['nom'],
            insee=properties['insee'],
            departement_id=parent_zupc.departement_id,
            # 4326 is a reference to https://spatialreference.org/ref/epsg/wgs-84/
            shape=from_shape(multipolygon, srid=4326),
            parent_id=parent_zupc.id
        )
        db.session.add(obj)
    db.session.flush()
def load_zupc_tmp_table(contours_shape_filename, arrondissements_shape_filename, zupc_repo):
    recreate_zupc_tmp_table()
    fill_zupc_tmp_table_from_contours(contours_shape_filename)
    fill_arrondissements(arrondissements_shape_filename)
    fill_zupc_tmp_table_from_arretes(zupc_repo)


def merge_zupc_tmp_table():
    """zupc_temp table contains the entries to insert into table ZUPC.

    - insert all entries from zupc_temp to ZUPC (so each new ZUPC gets a new id)
    - update the new ZUPC field "parent_id" to reference the parent
    - update table ADS to reference the new ZUPC
    - remove "old" ZUPC entries
    """
    if db.session.query(ADS) \
                 .outerjoin(ZUPC_tmp, ADS.insee == ZUPC_tmp.insee) \
                 .filter(ZUPC_tmp.id.is_(None)) \
                 .count() > 0:
        raise ValueError('Some INSEE codes referenced in table ADS do not exist in table zupc_temp')

    last_zupc_id = db.session.query(func.MAX(ZUPC.id)).one()[0]

    logger.info('Insert data from zupc_temp to ZUPC')
    db.session.execute('''
        INSERT INTO "ZUPC"(departement_id, nom, insee, shape, active)
        SELECT departement_id, nom, insee, shape, false FROM zupc_temp
    ''')

    db.session.flush()

    # For each ZUPC that has a parent in table zupc_temp:
    # - find the parent created just before in table ZUPC
    # - find the child
    # - update the child with the parent's id
    query = db.session.query(ZUPC_tmp).filter(ZUPC_tmp.parent_id != ZUPC_tmp.id)
    logger.info('Update ZUPC.parent_id of %s rows', query.count())
    for row in query:
        parent_zupc = db.session.query(ZUPC) \
                                .filter(ZUPC.id > last_zupc_id) \
                                .filter(ZUPC.insee == row.parent.insee).one()

        zupc = db.session.query(ZUPC) \
                         .filter(ZUPC.id > last_zupc_id) \
                         .filter(ZUPC.insee == row.insee).one()

        zupc.parent_id = parent_zupc.id
        db.session.add(zupc)

    # Update ADS to reference the new ZUPC
    insee_zupc = {
        zupc.insee: zupc.id
        for zupc in
        db.session.query(ZUPC.id, ZUPC.insee).filter(ZUPC.id > last_zupc_id)
    }
    query = db.session.query(ADS)
    logger.info('Update ADS.zupc_id of %s rows', query.count())
    for ads in query:
        ads.zupc_id = insee_zupc[ads.insee]
        db.session.add(ads)

    # Remove old ZUPC entries
    query = db.session.query(ZUPC).filter(ZUPC.id <= last_zupc_id)
    logger.info('Remove %s outdated ZUPC', query.count())
    query.delete()

    db.session.commit()


@manager.option(
    '--contours-url',
    help='Contours URL to download, default=%s' % CONTOURS_DEFAULT_URL,
    default=CONTOURS_DEFAULT_URL
)
@manager.option(
    '--arrondissements-url',
    help='Arrondissements URL to download, default=%s' % CONTOURS_DEFAULT_URL,
    default=ARRONDISSEMENTS_DEFAULT_URL
)
@manager.option(
    '--contours-tmpdir',
    help='Where --contours-url is downloaded and extracted, default=%s' % CONTOURS_DEFAULT_TMPDIR,
    default=CONTOURS_DEFAULT_TMPDIR
)
@manager.option(
    '--zupc-repo',
    help='Directory where https://github.com/openmaraude/ZUPC has been cloned, default=%s' % ZUPC_DEFAULT_DIRECTORY,
    default=ZUPC_DEFAULT_DIRECTORY
)
def import_zupc(contours_url, contours_tmpdir, zupc_repo):
    # Ensure zupc_repo has been cloned
    if not os.path.exists(zupc_repo):
        raise ValueError('Please clone https://github.com/openmaraude/ZUPC to %s or set --zupc-dir option to the '
                         'cloned directory' % zupc_repo)

    # Developers: set CONTOURS_DONT_DOWNLOAD=1 if files have already been downloaded.
    if os.environ.get('CONTOURS_DONT_DOWNLOAD') not in TRUE_VARS:
        download_zipfile(contours_url, contours_tmpdir)

    shape_filenames = list(find_files_by_extension(contours_tmpdir, 'shp'))
    if len(shape_filenames) != 1:
        raise RuntimeError('None or more than one shapefile .shp in %s' % contours_tmpdir)

    arrondissements_shape_filenames = list(find_files_by_extension(arrondissements_tmpdir, 'shp'))
    if len(arrondissements_shape_filenames) != 1:
        raise RuntimeError('None or more than one shapefile .shp in %s' % arrondissements_tmpdir)

    load_zupc_tmp_table(contours_shape_filenames[0], arrondissements_shape_filenames[0], zupc_repo)
    merge_zupc_tmp_table()
