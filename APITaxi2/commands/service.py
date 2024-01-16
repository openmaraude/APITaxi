import click
from flask import Blueprint, current_app
from sqlalchemy import func, cast
from sqlalchemy.orm import joinedload

from APITaxi_models2 import (
    db,
    ADS,
    Taxi,
    Town,
    ZUPC,
)
from APITaxi_models2.gare import GareVoyageur, CentreVille

from APITaxi2.exclusions import ExclusionHelper


blueprint = Blueprint('commands_service', __name__, cli_group=None)


def _taxis_search(lon, lat, exclusions=False):
    """Get the number of taxis potentially available at a location.

    Doesn't take into account current avaibility but all registred taxis allowed at this location.
    From their ADS alone, or from belonging to a ZUPC.

    If "exclusions" is true, take into account the exclusion rules.
    """
    # Prior to searching taxis, is the client in a zone where cruising is allowed?
    if exclusions:
        exclusion_helper = ExclusionHelper()
        if exclusion_helper.is_at_excluded_zone(lon, lat):
            return 0

    # First ask in what town the location is
    towns = Town.query.filter(
        func.ST_Intersects(Town.shape, f'POINT({lon} {lat})'),
    ).all()  # Shouldn't happen but in case geometries overlap on OSM
    if not towns:
        return 0
    town = towns[0]
    current_app.logger.debug('town=%s', town)

    # Now ask the potential ZUPCs the town is part of
    # There may be several: union of towns, airport, TGV station...
    zupcs = ZUPC.query.options(
        joinedload(ZUPC.allowed)
    ).filter(
        ZUPC.allowed.contains(town)
    ).all()

    # Now we know the taxis allowed at this position are the ones from this town
    # plus the potential other taxis from the ZUPC
    allowed_insee_codes = {town.insee, *(town.insee for zupc in zupcs for town in zupc.allowed)}
    current_app.logger.debug('allowed_insee_codes=%s', allowed_insee_codes)

    # Fetch all Taxi and VehicleDescriptions objects related to "locations".
    query = db.session.query(Taxi).join(
        ADS
    ).filter(
        ADS.insee.in_(allowed_insee_codes)
    )
    current_app.logger.debug('query=%s', query)

    return query.count()


@blueprint.cli.group()
def service():
    """Taxi service in different situations"""


@service.command()
@click.option(
    "--drg",
    type=str,
    help='Segment DRG',
)
def gares(drg):
    query = db.session.query(
        GareVoyageur,
        CentreVille.population,
        func.ST_Distance(
            GareVoyageur.wgs_84,
            CentreVille.wgs_84,
        ),
    ).join(
        CentreVille, CentreVille.insee == func.concat(GareVoyageur.departement_numero, GareVoyageur.commune_code),
    ).filter(
        GareVoyageur.latitude_entreeprincipale_wgs84.isnot(None),
        GareVoyageur.longitude_entreeprincipale_wgs84.isnot(None),
    ).order_by(
        GareVoyageur.gare_alias_libelle_noncontraint
    )
    if drg:
        query = query.filter(
            func.lower(GareVoyageur.segmentdrg_libelle) == drg
        )

    for gare, population, distance in query:
        print(
            gare.gare_alias_libelle_noncontraint,
            _taxis_search(
                gare.longitude_entreeprincipale_wgs84,
                gare.latitude_entreeprincipale_wgs84,
            ),
            population,
            round(distance / 1000, 1),
            sep='\t'
        )
