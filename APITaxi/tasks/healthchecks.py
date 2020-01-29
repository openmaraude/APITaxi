from APITaxi.extensions import celery
from APITaxi_utils.healthchecks import all_healthchecks

@celery.task
def task_healthchecks():
    return all_healthchecks(with_task=False)
