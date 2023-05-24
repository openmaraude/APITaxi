from celery import shared_task

from .clean import clean_geoindex_timestamps  # noqa
from .operators import handle_hail_timeout, send_request_operator  # noqa
from .stats import store_active_taxis  # noqa
from .. import clean_db


@shared_task(name='blur_geotaxi')
def task_blur_geotaxi():
    count = clean_db.blur_geotaxi()
    print(f"{count} geotaxi blurred")


@shared_task(name='blur_hails')
def task_blur_hails():
    count = clean_db.blur_hails()
    print(f"{count} hails blurred")


@shared_task(name='compute_stats_hails')
def task_compute_stats_hails():
    count = clean_db.compute_stats_hails()
    print(f"{count} hails added to stats")


@shared_task(name='delete_old_hails')
def task_delete_old_hails():
    count = clean_db.delete_old_hails()
    print(f"{count} hails deleted")


@shared_task(name='delete_old_taxis')
def task_delete_old_taxis():
    count = clean_db.delete_old_taxis()
    print(f"{count} old taxis deleted")


@shared_task(name='delete_old_orphans')
def task_delete_old_orphans():
    driver_count, ads_count, vehicle_count, customer_count = clean_db.delete_old_orphans()
    print(f"{driver_count} old drivers deleted")
    print(f"{ads_count} old ADS deleted")
    print(f"{vehicle_count} old vehicle descriptions deleted")
    print(f"{customer_count} old customer accounts deleted")
