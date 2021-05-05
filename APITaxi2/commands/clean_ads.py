from pathlib import Path

from flask import Blueprint
from sqlalchemy import func
from sqlalchemy.orm import joinedload
import yaml

from APITaxi_models2 import db, ADS, Hail, Taxi


blueprint = Blueprint('commands_ads', __name__, cli_group=None)


def repr_ads(ads):
    return f'{ads.id} insee={ads.insee} numero={ads.numero} added_by={ads.added_by_id}'


def update_ref_ads(to_remove, to_keep):
    # As (vehicle_id, ads_id, driver_id, added_by) must be unique
    # we can't just change the ads_id if there is already a taxi using the ADS to keep
    existing_taxi = Taxi.query.filter(
        Taxi.ads == to_keep
    ).order_by(
        Taxi.added_at.desc()
    ).first()
    # The list of taxis to remove, so we can delete their ADS
    taxis_to_remove = Taxi.query.filter(
        Taxi.ads_id.in_(row.id for row in to_remove)
    ).order_by(
        Taxi.added_at.desc()
    ).all()
    if existing_taxi:
        print(f"\t\tThere is already a taxi using the ADS {repr_ads(to_keep)}")
    else:
        # We must chose one taxi to give the new ADS, and delete the others
        # This case doesn't happen on a production database
        existing_taxi = taxis_to_remove.pop()
        print(f"\t\tReusing the latest taxi {existing_taxi} to use the ADS {repr_ads(to_keep)}")
        existing_taxi.ads = to_keep
        db.session.flush()
    # For the taxis left to remove, reassign the related objects
    if taxis_to_remove:
        for hail in Hail.query.filter(Hail.taxi_id.in_(row.id for row in taxis_to_remove)):
            hail.taxi = existing_taxi
        db.session.flush()
        # Now the taxis can be deleted for the obsolete ADS to be deleted
        for taxi in taxis_to_remove:
            db.session.delete(taxi)


def remove_duplicates(old_insee, new_insee):
    duplicates = db.session.query(
        ADS.numero, ADS.added_by_id,
        func.COUNT().label('count')
    ).filter(
        ADS.insee.in_([old_insee, new_insee]),
    ).group_by(
        ADS.numero, ADS.added_by_id,
    ).having(func.COUNT() > 1)

    for dup in duplicates:
        print(f'ADS found {dup.count} duplicates: numero={dup.numero} added_by={dup.added_by_id}')

        # Keep the last one with the new INSEE
        to_keep = ADS.query.filter(
            ADS.insee == new_insee,
            ADS.numero == dup.numero,
            ADS.added_by_id == dup.added_by_id,
        ).order_by(
            ADS.added_at.desc()
        ).first()
        # Remove all the other ones
        to_remove = ADS.query.options(
            joinedload(ADS.town)  # XXX
        ).filter(
            ADS.insee.in_([old_insee, new_insee]),
            ADS.numero == dup.numero,
            ADS.added_by_id == dup.added_by_id,
            ADS.id != to_keep.id,
        ).all()

        print(f'\t\tKeep: {repr_ads(to_keep)}')
        print(f'\t\tRemove: {", ".join(repr_ads(ads) for ads in to_remove)}')

        update_ref_ads(to_remove, to_keep)
        db.session.flush()

        for obj in to_remove:
            db.session.delete(obj)

    db.session.commit()


@blueprint.cli.command('clean_ads', help='Clean database')
def clean_ads():
    # Taken from the ZUPC repo
    fusion_filename = Path(__file__) / "../2020.yaml"
    with open(fusion_filename.resolve()) as handle:
        fusion_data = yaml.safe_load(handle)

    for old_insee, new_insee in fusion_data['mapping'].items():
        remove_duplicates(old_insee, new_insee)
