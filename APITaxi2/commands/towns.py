import os
import pathlib
import requests
from urllib.parse import urlparse
import zipfile

import click
from flask import Blueprint, current_app
from geoalchemy2.shape import from_shape
from shapely.geometry import shape, MultiPolygon
import shapefile

from APITaxi_models2 import db, Town


blueprint = Blueprint('commands_towns', __name__, cli_group=None)


# Archive downloaded and extracted to CONTOURS_DIR
CONTOURS_DEFAULT_URL = "http://osm13.openstreetmap.fr/~cquest/openfla/export/communes-20210101-shp.zip"

# Temporary path where CONTOURS_URL is downloaded
CONTOURS_DEFAULT_TMPDIR = '/tmp/temp_contours'


def to_multipolygon(shape_obj):
    """The contours dump is now using both polygons and multipolygons."""
    if not isinstance(shape_obj, MultiPolygon):
        shape_obj = MultiPolygon([shape_obj])
    return shape_obj


def download_zipfile(url, download_path):
    """Download and extract ZIP file from `url` to `download_path`.
    """
    filename = pathlib.Path(urlparse(url).path).name
    fullpath = download_path / filename

    if fullpath.exists():
        print(f"{filename} has already been downloaded, delete to download it again")
    else:
        os.makedirs(download_path)
        print(f'Download {url} to {fullpath}')
        r = requests.get(url)
        with open(fullpath, 'wb') as handle:
            handle.write(r.content)

    with zipfile.ZipFile(fullpath) as archive:
        print(f'Extract {fullpath} to {download_path}')
        archive.extractall(download_path)


def get_records_from_shapefile(shape_filename):
    """Yield records from `shape_filename`.
    """
    reader = shapefile.Reader(str(shape_filename))
    for shape_record in reader.iterShapeRecords():
        feature = shape_record.__geo_interface__
        yield feature['geometry'], feature['properties']


def update_towns_from_contours(shape_filename):
    """Build ZUPC temporary table. Rows only contain data from the contours database and need to be "completed" with
    data from the ZUPC repository.
    """
    print("Update towns from the new contours...")

    insee_codes_seen = set()

    for geom, properties in get_records_from_shapefile(shape_filename):
        # geom is in the GeoJSON format
        # 4326 is a reference to https://spatialreference.org/ref/epsg/wgs-84/
        new_shape = from_shape(to_multipolygon(shape(geom)), srid=4326)
        town = db.session.query(Town).filter(Town.insee == properties['insee']).one_or_none()
        if town:
            # Update
            town.name = properties['nom']
            town.shape = new_shape
        else:
            # Insert
            town = Town(
                name=properties['nom'],
                insee=properties['insee'],
                shape=new_shape,
            )
            current_app.logger.info("Inserting new town %s (%s)", town.name, town.insee)

        db.session.add(town)
        insee_codes_seen.add(properties['insee'])

    # Remove insee codes no longer used, so they better be removed from the relationships
    for old_town in db.session.query(Town).filter(Town.insee.notin_(insee_codes_seen)):
        current_app.logger.info("Deleting old town %s (%s)", old_town.name, old_town.insee)
        db.session.delete(old_town)

    db.session.commit()
    print("Done")


class PathlibPath(click.Path):
    """click.Path does not convert to a Path object."""

    def convert(self, *args):
        return pathlib.Path(super().convert(*args))


PATH = PathlibPath()


@blueprint.cli.command('import_towns')
@click.option(
    '--contours-url', default=CONTOURS_DEFAULT_URL,
    help='Contours URL to download, default=%s' % CONTOURS_DEFAULT_URL
)
@click.option(
    '--contours-tmpdir', default=CONTOURS_DEFAULT_TMPDIR, type=PATH,
    help='Where --contours-url is downloaded and extracted, default=%s' % CONTOURS_DEFAULT_TMPDIR
)
def import_towns(contours_url, contours_tmpdir):
    download_zipfile(contours_url, contours_tmpdir)

    shape_filenames = list(contours_tmpdir.glob('*.shp'))
    if len(shape_filenames) != 1:
        raise RuntimeError('None or more than one shapefile .shp in %s' % contours_tmpdir)

    update_towns_from_contours(shape_filenames[0])
