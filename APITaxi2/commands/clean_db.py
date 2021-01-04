import click
from flask import Blueprint
from sqlalchemy import and_, func
from sqlalchemy.orm import joinedload, make_transient

from APITaxi_models2 import db, ADS, Driver, Hail, Taxi, Vehicle, VehicleDescription


blueprint = Blueprint('commands_clean', __name__, cli_group=None)


def remove_duplicates(Model, fields, update_ref):
    """Filter all Model objects group by "fields" with more than one entry. For
    each result, only keep the latest object (more recent Model.added_at) and
    remove the older entries.

    update_ref callback is called with (to_remove, new_reference) to update
    other models referencing the entries before removal.
    """
    duplicates = db.session.query(
        *fields,
        func.COUNT().label('count')
    ).group_by(
        *fields
    ).having(func.COUNT() > 1)

    for dup in duplicates:
        print(f'{Model.__tablename__} found {dup.count} duplicates: {" ".join("%s=%-10s" % (str(field), dup[idx]) for idx, field in enumerate(fields))}')

        objs = Model.query.filter(
            *[field == dup[idx] for idx, field in enumerate(fields)]
        ).order_by(Model.added_at.desc()).all()
        to_keep = objs[0]
        to_remove = objs[1:]

        print(f'\t               Keep: {to_keep}')
        print(f'\t             Remove: {", ".join(str(e) for e in to_remove)}')

        update_ref(to_remove, to_keep)
        db.session.flush()

        for obj in to_remove:
            db.session.delete(obj)

        db.session.commit()


def remove_sharing_ads():
    """For each taxi, if added_by is != ads.added_by, duplicate the ADS."""
    # Duplicate ADS
    query = Taxi.query.options(joinedload(Taxi.ads)).outerjoin(ADS).filter(
        Taxi.added_by_id != ADS.added_by_id
    )
    count = query.count()
    if not count:
        return

    print(f'Taxi is linked to {count} ADS with different added_by. Duplicate ADS.')
    for taxi in query:
        prev_ads = taxi.ads_id
        existing = ADS.query.filter_by(
            numero=taxi.ads.numero,
            insee=taxi.ads.insee,
            added_by_id=taxi.added_by_id
        ).first()

        # If an ADS has already been registered by the taxi's operator, use it
        if existing:
            taxi.ads = existing
            print(f'\tSet ADS {existing.id} to taxi {taxi.id} instead of {prev_ads}')
        # Otherwise, duplicate it
        else:
            ads = ADS(
                # Duplicate fields
                numero=taxi.ads.numero,
                doublage=taxi.ads.doublage,
                insee=taxi.ads.insee,
                vehicle_id=taxi.ads.vehicle_id,
                category=taxi.ads.category,
                owner_name=taxi.ads.owner_name,
                owner_type=taxi.ads.owner_type,
                zupc_id=taxi.ads.zupc_id,

                # HistoryMixin fields
                added_via=taxi.ads.added_via,
                source=taxi.ads.source,
                added_at=func.NOW(),
                last_update_at=func.NOW(),

                # Update added_by
                added_by_id=taxi.added_by_id,
            )
            taxi.ads = ads
            db.session.add(ads)
            db.session.flush()
            print(f'\tCreate new ADS {ads.id}, and replace taxi {taxi.id} ADS {prev_ads} with it')

    db.session.commit()


def remove_sharing_driver():
    """For each taxi, if added_by is != driver.added_by, duplicate the driver."""
    # Duplicate Driver
    query = Taxi.query.options(joinedload(Taxi.driver)).outerjoin(Driver).filter(
        Taxi.added_by_id != Driver.added_by_id
    )
    count = query.count()
    if not count:
        return

    print(f'Taxi is linked to {count} Driver with different added_by. Duplicate Driver.')
    for taxi in query:
        prev_driver = taxi.driver_id
        existing = Driver.query.filter_by(
            departement_id=taxi.driver.departement_id,
            professional_licence=taxi.driver.professional_licence,
            added_by_id=taxi.added_by_id
        ).first()

        if existing:
            taxi.driver = existing
            print(f'\tSet Driver {existing.id} to taxi {taxi.id} instead of {prev_driver}')
        else:
            driver = Driver(
                # Duplicate fields
                departement_id=taxi.driver.departement_id,
                birth_date=taxi.driver.birth_date,
                first_name=taxi.driver.first_name,
                last_name=taxi.driver.last_name,
                professional_licence=taxi.driver.professional_licence,

                # HistoryMixin fields
                added_via=taxi.driver.added_via,
                source=taxi.driver.source,
                added_at=func.NOW(),
                last_update_at=func.NOW(),

                # Update added_by
                added_by_id=taxi.added_by_id
            )
            taxi.driver = driver
            db.session.add(driver)
            db.session.flush()
            print(f'\tCreate new Driver {driver.id}, and replace taxi {taxi.id} ADS {prev_driver} with it')

    db.session.commit()


def remove_orphans(ModelA, ModelB, on_clause=None):
    """Remove ModelA entries with no references from ModelB.
    """
    if on_clause is None:
        query = db.session.query(ModelA.id).outerjoin(ModelB)
    else:
        query = db.session.query(ModelA.id).outerjoin(ModelB, on_clause)

    query = query.filter(ModelB.id.is_(None))
    count = query.count()
    if not count:
        return

    print(f'{count} {ModelA.__name__} are not linked to {ModelB.__name__}. Remove them.')
    db.session.query(ModelA).filter(ModelA.id.in_(obj.id for obj in query)).delete(
        synchronize_session=False
    )
    db.session.commit()


@blueprint.cli.command('clean_db', help='Clean database')
def clean_db():
    #
    # Remove objects sharing
    #
    remove_sharing_ads()
    remove_sharing_driver()

    #
    # Remove duplicates
    #
    def ref_ads(to_remove, new_ref):
        taxis = Taxi.query.filter(Taxi.ads_id.in_([row.id for row in to_remove])).all()
        print(f'\tTaxis using old ADS: {", ".join(taxi.id for taxi in taxis)}')
        for taxi in taxis:
            taxi.ads = new_ref

    remove_duplicates(ADS, (ADS.insee, ADS.numero, ADS.added_by_id), ref_ads)


    def ref_driver(to_remove, new_ref):
        taxis = Taxi.query.filter(Taxi.driver_id.in_([row.id for row in to_remove])).all()
        print(f'\tTaxis using old driver: {", ".join(taxi.id for taxi in taxis)}')
        for taxi in taxis:
            taxi.driver = new_ref

    remove_duplicates(Driver, (Driver.departement_id, Driver.professional_licence, Driver.added_by_id), ref_driver)


    def ref_taxi(to_remove, new_ref):
        hails = Hail.query.filter(Hail.taxi_id.in_([row.id for row in to_remove])).all()
        print(f'\tHails using old taxi: {", ".join(hail.id for hail in hails)}')
        for hail in hails:
            hail.taxi = new_ref

    remove_duplicates(Taxi, (Taxi.ads_id, Taxi.vehicle_id, Taxi.driver_id, Taxi.added_by_id), ref_taxi)

    remove_orphans(Vehicle, VehicleDescription)
    remove_orphans(Driver, Taxi)
    remove_orphans(ADS, Taxi)
    remove_orphans(VehicleDescription, Taxi, VehicleDescription.vehicle_id == Taxi.vehicle_id)
