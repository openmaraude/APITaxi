import json
from unicodedata import name

import click
from flask import Blueprint, current_app
from geoalchemy2.shape import from_shape
from shapely.geometry import shape, MultiPolygon

from APITaxi2 import exclusions
from APITaxi_models2 import db, Exclusion


blueprint = Blueprint('commands_exclusion', __name__, cli_group=None)


@blueprint.cli.group()
def exclusion():
    """Manage exclusion zones"""


@exclusion.command()
@click.argument("GeoJSON-file", type=click.File('rb'))
def add(geojson_file):
    """Add or update a single zone from a GeoJSON file."""
    geojson = json.load(geojson_file)

    assert geojson['type'] == "Feature"
    osm_id = geojson['id']
    name = geojson['properties'].get('name:fr') or geojson['properties'].get('name', osm_id)
    shapely_shape = shape(geojson['geometry'])
    if not isinstance(shapely_shape, MultiPolygon):
        shapely_shape = MultiPolygon([shapely_shape])
    wkb_element = from_shape(shapely_shape, srid=4326)
    exclusion = db.session.query(Exclusion).filter(Exclusion.id == osm_id).one_or_none()
    if exclusion:
        # Update
        exclusion.name = name
        exclusion.shape = wkb_element
    else:
        # Insert
        exclusion = Exclusion(
            id=osm_id,
            name=name,
            shape=wkb_element,
        )
        current_app.logger.info("Inserting new exclusion %s", name)

    db.session.add(exclusion)
    db.session.commit()

    exclusions.ExclusionHelper().reset()


@exclusion.command()
@click.argument("exclusion_id")
def remove(exclusion_id):
    """Remove ZUPC"""
    exclusion = db.session.query(Exclusion).filter(Exclusion.id == exclusion_id).one()

    click.echo(f"Way ID {name.id}")
    click.echo(f"Name: {exclusion.name}")
    if click.confirm("Delete?"):
        db.session.delete(exclusion)
        db.session.commit()

    exclusions.ExclusionHelper().reset()


@exclusion.command()
def reset():
    """Reset cache of excluded zones"""
    exclusions.ExclusionHelper().reset()
