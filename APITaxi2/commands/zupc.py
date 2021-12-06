import json
import pathlib
import sys
import yaml

import click
from flask import Blueprint, current_app
from sqlalchemy import func
from APITaxi_models2 import db, Town, ZUPC
from APITaxi_models2.zupc import town_zupc


blueprint = Blueprint('commands_zupc', __name__, cli_group=None)


# Directory where https://github.com/openmaraude/ZUPC has been cloned
ZUPC_DEFAULT_DIRECTORY = '/tmp/ZUPC'


def fill_zupc_union(zupc_dir):
    """Each file "zone.yaml" in the given directory contains the list of INSEE codes
    covered by each ZUPC. This function reads the zone description and:

    - create the a new zone of the given name;
    - set the the list of allowed towns to this list.

    Only drivers having a licence from one of these towns will then be visible from inside the ZUPC.
    """
    with open(zupc_dir / 'zone.yaml') as handle:
        zone = yaml.safe_load(handle)

    # Read as numbers by the YAML parser but they are alphanumerical (Bastia = '2B033')
    insee_codes = zone['allowed'].keys()

    # All INSEE codes should have been imported from the communes file
    towns = Town.query.filter(Town.insee.in_(insee_codes)).all()
    assert len(towns) == len(insee_codes)

    # Geometry
    if zone.get('feature') or zone.get('include') or zone.get('exclude'):
        raise NotImplementedError("ZUPC shapes are only computed for now")

    zupc = db.session.query(ZUPC).filter(ZUPC.zupc_id == zone['id']).one_or_none()
    if zupc:
        # Update
        zupc.nom = zone['name']
    else:
        # Insert
        zupc = ZUPC(
            zupc_id=zone['id'],
            nom=zone['name'],
        )

    db.session.add(zupc)
    db.session.flush()

    # Rebind the towns part of a ZUPC
    zupc.allowed.clear()
    zupc.allowed.extend(towns)
    db.session.flush()


def fill_zupc(zupc_dir):
    """Insert informations into zupc_temp table.
    """
    current_app.logger.debug('Fill ZUPC temporary table with %s', zupc_dir)

    if not (zupc_dir / 'zone.yaml').exists():
        current_app.logger.debug('No zone.yaml file in %s, nothing to do', zupc_dir)
        return

    fill_zupc_union(zupc_dir)


def fill_zupc_table_from_arretes(zupc_repo):
    """Fill informations in ZUPC table from "arrêtés" stored in --zupc_repo.

    Each folder in the root directory of the ZUPC repository contains the files describing a ZUPC.
    """
    for zupc_dir in zupc_repo.iterdir():
        fullpath = zupc_repo / zupc_dir

        # Skip extra files
        if fullpath.is_file():
            continue

        if "ZUPC" in zupc_dir.name:
            fill_zupc(fullpath)

        # Skip train and airport stations for now

    db.session.commit()


class PathlibPath(click.Path):
    """click.Path does not convert to a Path object."""

    def convert(self, *args):
        return pathlib.Path(super().convert(*args))


PATH = PathlibPath()


@blueprint.cli.command('import_zupc')
@click.option(
    '--zupc-repo', default=ZUPC_DEFAULT_DIRECTORY, type=PATH,
    help='Directory where https://github.com/openmaraude/ZUPC has been cloned, default=%s' % ZUPC_DEFAULT_DIRECTORY
)
def import_zupc(zupc_repo):
    # Ensure zupc_repo has been cloned
    if not zupc_repo.exists():
        raise ValueError('Please clone https://github.com/openmaraude/ZUPC to %s or set --zupc-dir option to the '
                         'cloned directory' % zupc_repo)

    # Delete existing zones beforehand?
    fill_zupc_table_from_arretes(zupc_repo)


@blueprint.cli.command('export_zupc')
def export_zupc():
    """Export the list of ZUPC as a GeoJSON map to share."""

    output = {
        'type': "FeatureCollection",
        'features': []
    }

    query = db.session.query(
        ZUPC,
        func.ST_AsGeoJSON(
            func.ST_Union(  # Aggregate function
                func.Geometry(  # Geometry type needed
                    Town.shape
                )
            )
        ),
        func.json_agg(Town.insee),
    ).join(
        town_zupc, town_zupc.c.zupc_id == ZUPC.id
    ).join(
        Town
    ).group_by(
        ZUPC.id
    ).order_by(
        ZUPC.id  # Consistent order across exports
    )

    for zupc, zupc_shape, insee_codes in query:
        output['features'].append({
            'type': "Feature",
            'geometry': json.loads(zupc_shape),
            'properties': {
                'zupc_id': zupc.zupc_id,
                'name': zupc.nom,
                'insee': insee_codes,
            }
        })

    json.dump(output, sys.stdout, indent=2)
    sys.stdout.flush()
