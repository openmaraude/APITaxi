import click
from flask import Blueprint
from sqlalchemy.orm import joinedload
from sqlalchemy import func

from APITaxi_models2 import db, ADS, Driver, Taxi, User, Vehicle, VehicleDescription


blueprint = Blueprint('commands_clean', __name__, cli_group=None)


def check_duplicates(Model, fields):
    """Filter all Model objects group by "fields" with more than one entry."""
    duplicates = db.session.query(
        *fields,
        func.COUNT().label('count')
    ).group_by(
        *fields
    ).having(func.COUNT() > 1)

    count = duplicates.count()
    if count:
        print(f'{Model.__tablename__} found {count} duplicates.')


def check_sharing_ads():
    """For each taxi, if added_by is != ads.added_by, the ADS is shared."""
    query = Taxi.query.options(joinedload(Taxi.ads)).outerjoin(ADS).filter(
        Taxi.added_by_id != ADS.added_by_id
    )
    count = query.count()
    if count:
        print(f'Taxi is linked to {count} ADS with different added_by. Duplicate ADS.')


def check_sharing_driver():
    """For each taxi, if added_by is != driver.added_by, the driver is shared."""
    query = Taxi.query.options(joinedload(Taxi.driver)).outerjoin(Driver).filter(
        Taxi.added_by_id != Driver.added_by_id
    )
    count = query.count()
    if count:
        print(f'Taxi is linked to {count} Driver with different added_by. Duplicate Driver.')


def check_orphans(Model, query, remove=False):
    """Remove Model entries if id is returned by query.
    """
    count = query.count()
    if not count:
        return

    print(f'{count} {Model.__name__} entries are orphan.{ "Remove them." if remove else ""}')

    # Vehicles don't have added_by
    if Model != Vehicle:
        print()
        print(f'{"operator":>30} | count')
        print("-" * 30, "|", "-" * 5)
        print("\n".join(
            f'{email:>30} | {count:5}'
            for email, count in query.from_self(User.email, func.count(Model.id))
            .join(User)
            .group_by(User.email)
            .order_by(func.count(Model.id).desc())
        ))
        print()

    if not remove:
        return

    db.session.query(Model).filter(Model.id.in_(obj.id for obj in query)).delete(
        synchronize_session=False
    )
    db.session.commit()


@ blueprint.cli.command('clean_db', help='Check the database is clean')
@ click.option('--remove-orphans', is_flag=True, help='Only remove orphans if asked so')
def clean_db(remove_orphans):
    check_sharing_ads()
    check_sharing_driver()

    check_duplicates(ADS, (ADS.insee, ADS.numero, ADS.added_by_id))
    check_duplicates(Driver, (Driver.departement_id, Driver.professional_licence, Driver.added_by_id))
    check_duplicates(Taxi, (Taxi.ads_id, Taxi.vehicle_id, Taxi.driver_id, Taxi.added_by_id))

    check_orphans(
        Driver,
        Driver.query.outerjoin(Taxi).filter(Taxi.id.is_(None)),
        remove=remove_orphans,
    )

    check_orphans(
        ADS,
        ADS.query.outerjoin(Taxi).filter(Taxi.id.is_(None)),
        remove=remove_orphans,
    )

    check_orphans(
        VehicleDescription,
        VehicleDescription.query.outerjoin(
            Taxi, VehicleDescription.vehicle_id == Taxi.vehicle_id
        ).filter(
            Taxi.id.is_(None)
        ),
        remove=remove_orphans,
    )

    check_orphans(
        Vehicle,
        Vehicle.query.outerjoin(Taxi).outerjoin(
            ADS,
            ADS.vehicle_id == Vehicle.id
        ).filter(
            Taxi.id.is_(None),
            ADS.id.is_(None)
        ),
        remove=remove_orphans,
    )
