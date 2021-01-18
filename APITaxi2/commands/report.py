import datetime

import click
from flask import Blueprint
from prettytable import PrettyTable
from sqlalchemy.orm import joinedload

from APITaxi_models2 import ADS, Departement, Driver, Hail, Taxi, User, VehicleDescription


blueprint = Blueprint('commands_report', __name__, cli_group=None)


TODAY = datetime.datetime.now().date()

# Monday of last week
START_LAST_WEEK = TODAY - datetime.timedelta(days=TODAY.weekday() + 7)
# This monday
END_LAST_WEEK = TODAY - datetime.timedelta(days=TODAY.weekday())


def display_model(query, fields):
    table = PrettyTable()
    table.field_names = [field[0] for field in fields]
    table.add_rows([
        [field[1](obj) for field in fields]
        for obj in query
    ])

    print(table)


@blueprint.cli.command('report')
@click.option('--since', type=click.DateTime(), default=str(START_LAST_WEEK))
@click.option('--until', type=click.DateTime(), default=str(END_LAST_WEEK))
def report(since, until):
    """Output to stdout all objects created between two dates. Used to
    generate weekly API usage reports."""
    print(f'=== ADS created between {since.strftime("%d/%m/%Y")} and {until.strftime("%d/%m/%Y")} ===')
    display_model(
        ADS.query.options(
            joinedload(ADS.added_by)
        ).join(User).filter(
            ADS.added_at >= since,
            ADS.added_at < until
        ).order_by(ADS.added_at, ADS.id),
        [
            ('Création', lambda ads: ads.added_at),
            ('Id', lambda ads: ads.id),
            ('Numéro', lambda ads: ads.numero),
            ('INSEE', lambda ads: ads.insee),
            ('Propriétaire', lambda ads: ads.owner_name),
            ('Opérateur', lambda ads: ads.added_by.email),
        ]
    )

    print(f'\n=== Driver created between {since.strftime("%d/%m/%Y")} and {until.strftime("%d/%m/%Y")} ===')
    display_model(
        Driver.query.options(
            joinedload(Driver.departement),
            joinedload(Driver.added_by)
        ).join(Departement).filter(
            Driver.added_at >= since,
            Driver.added_at < until
        ).order_by(Driver.added_at, Driver.id),
        [
            ('Création', lambda driver: driver.added_at),
            ('Id', lambda driver: driver.id),
            ('Prénom/Nom', lambda driver: f'{driver.first_name} {driver.last_name}'),
            ('Département', lambda driver: f'{driver.departement.numero} - {driver.departement.nom}'),
            ('Licence pro.', lambda driver: driver.professional_licence),
            ('Opérateur', lambda driver: driver.added_by.email),
        ]
    )

    print(f'\n=== Vehicles created between {since.strftime("%d/%m/%Y")} and {until.strftime("%d/%m/%Y")} ===')
    display_model(
        VehicleDescription.query.options(
            joinedload(VehicleDescription.added_by)
        ).filter(
            VehicleDescription.added_at >= since,
            VehicleDescription.added_at < until
        ).order_by(VehicleDescription.added_at, VehicleDescription.id),
        [
            ('Création', lambda vd: vd.added_at),
            ('Id', lambda vd: vd.id),
            ('Opérateur', lambda vd: vd.added_by.email),
        ]
    )

    print(f'\n=== Taxis created between {since.strftime("%d/%m/%Y")} and {until.strftime("%d/%m/%Y")} ===')
    display_model(
        Taxi.query.options(
            joinedload(Taxi.added_by),
            joinedload(Taxi.vehicle)
        ).filter(
            Taxi.added_at >= since,
            Taxi.added_at < until
        ).order_by(Taxi.added_at),
        [
            ('Création', lambda taxi: taxi.added_at),
            ('Id', lambda taxi: taxi.id),
            ('ADS Id', lambda taxi: taxi.ads_id),
            ('Driver Id', lambda taxi: taxi.driver_id),
            ('Vehicle', lambda taxi: taxi.vehicle.licence_plate),
            ('Opérateur', lambda taxi: taxi.added_by.email),
        ]
    )

    print(f'\n=== Hails created between {since.strftime("%d/%m/%Y")} and {until.strftime("%d/%m/%Y")} ===')
    display_model(
        Hail.query.options(
            joinedload(Hail.added_by),
            joinedload(Hail.operateur)
        ).filter(
            Hail.added_at >= since,
            Hail.added_at < until
        ).order_by(Hail.added_at),
        [
            ('Création', lambda hail: hail.added_at),
            ('Id', lambda hail: hail.id),
            ('Client lon/lat', lambda hail: f'{hail.customer_lon}/{hail.customer_lat}'),
            ('Client addresse', lambda hail: hail.customer_address),
            ('Statut', lambda hail: hail.status),
            ('Moteur', lambda hail: hail.added_by.email),
            ('Opérateur', lambda hail: hail.operateur.email),
        ]
    )
