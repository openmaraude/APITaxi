from celery import Celery
from celery.schedules import crontab

celery = Celery(__name__)

from .clean import clean_geoindex_timestamps  # noqa
from .operators import handle_hail_timeout, send_request_operator  # noqa
from .stats import store_active_taxis  # noqa
from .. import clean_db


@celery.task(name='blur_geotaxi')
def task_blur_geotaxi():
    count = clean_db.blur_geotaxi()
    print(f"{count} geotaxi blurred")


@celery.task(name='blur_hails')
def task_blur_hails():
    count = clean_db.blur_hails()
    print(f"{count} hails blurred")


@celery.task(name='archive_hails')
def task_archive_hails():
    count = clean_db.archive_hails()
    print(f"{count} hails archived")


@celery.task(name='delete_old_taxis')
def task_delete_old_taxis():
    count = clean_db.delete_old_taxis()
    print(f"{count} old taxis deleted")


@celery.task(name='delete_old_orphans')
def task_delete_old_orphans():
    driver_count, ads_count, vehicle_count, customer_count = clean_db.delete_old_orphans()
    print(f"{driver_count} old drivers deleted")
    print(f"{ads_count} old ADS deleted")
    print(f"{vehicle_count} old vehicle descriptions deleted")
    print(f"{customer_count} old customer accounts deleted")


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(crontab(hour=4, minute=0), task_blur_geotaxi.s())
    sender.add_periodic_task(crontab(hour=4, minute=2), task_blur_hails.s())
    sender.add_periodic_task(crontab(hour=4, minute=4), task_archive_hails.s())
    sender.add_periodic_task(crontab(hour=4, minute=6), task_delete_old_taxis.s())
    sender.add_periodic_task(crontab(hour=4, minute=8), task_delete_old_orphans.s())
