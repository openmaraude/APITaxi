import datetime

import click
from flask import Blueprint
from prettytable import PrettyTable

from APITaxi_models2 import ADS, Driver, Hail, Taxi, VehicleDescription


blueprint = Blueprint('commands_report', __name__, cli_group=None)


TODAY = datetime.datetime.now().date()

# Monday of last week
START_LAST_WEEK = TODAY - datetime.timedelta(days=TODAY.weekday() + 7)
# This monday
END_LAST_WEEK = TODAY - datetime.timedelta(days=TODAY.weekday())


def display_model(query, fields):
    table = PrettyTable()
    table.field_names = [field.key for field in fields]
    table.add_rows([
        [getattr(row, field.key) for field in fields]
        for row in query
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
        ADS.query.filter(
            ADS.added_at >= since,
            ADS.added_at < until
        ).order_by(ADS.added_at, ADS.id),
        [
            ADS.added_at,
            ADS.id,
            ADS.numero,
            ADS.insee,
            ADS.owner_name
        ]
    )

    print(f'=== Driver created between {since.strftime("%d/%m/%Y")} and {until.strftime("%d/%m/%Y")} ===')
    display_model(
        Driver.query.filter(
            Driver.added_at >= since,
            Driver.added_at < until
        ).order_by(Driver.added_at, Driver.id),
        [
            Driver.added_at,
            Driver.id,
            Driver.first_name,
            Driver.last_name,
            Driver.departement_id,
            Driver.professional_licence
        ]
    )

    print(f'=== Vehicles created between {since.strftime("%d/%m/%Y")} and {until.strftime("%d/%m/%Y")} ===')
    display_model(
        VehicleDescription.query.filter(
            VehicleDescription.added_at >= since,
            VehicleDescription.added_at < until
        ).order_by(VehicleDescription.added_at, VehicleDescription.id),
        [
            VehicleDescription.added_at,
            VehicleDescription.id,
            VehicleDescription.internal_id
        ]
    )

    print(f'=== Taxis created between {since.strftime("%d/%m/%Y")} and {until.strftime("%d/%m/%Y")} ===')
    display_model(
        Taxi.query.filter(
            Taxi.added_at >= since,
            Taxi.added_at < until
        ).order_by(Taxi.added_at),
        [
            Taxi.added_at,
            Taxi.id,
            Taxi.ads_id,
            Taxi.driver_id,
            Taxi.vehicle_id,
        ]
    )

    print(f'=== Hails created between {since.strftime("%d/%m/%Y")} and {until.strftime("%d/%m/%Y")} ===')
    display_model(
        Hail.query.filter(
            Hail.added_at >= since,
            Hail.added_at < until
        ).order_by(Hail.added_at),
        [
            Hail.added_at,
            Hail.id,
            Hail.customer_lat,
            Hail.customer_lon,
            Hail.customer_address,
            Hail.status
        ]
    )
