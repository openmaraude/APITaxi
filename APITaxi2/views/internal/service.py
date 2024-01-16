from flask import current_app
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from APITaxi_models2 import (
    db,
    ADS,
    GareVoyageur,
    Taxi,
    Town,
    ZUPC,
)

from ...security import auth
from ...exclusions import ExclusionHelper


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


def service_gares():
    for gare in db.session.query(
        GareVoyageur
    ).filter(
        func.lower(GareVoyageur.segmentdrg_libelle) == 'a'  # Biggest stations
    ).order_by(
        GareVoyageur.alias_libelle_noncontraint
    ):
        print(
            gare.gare_alias_libelle_noncontraint,
            _taxis_search(
                float(gare.longitude_entreeprincipale_wgs84),
                float(gare.latitude_entreeprincipale_wgs84),
            ),
            sep='\t'
        )
    