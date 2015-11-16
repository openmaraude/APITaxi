from . import manager
from ..extensions import celery

@manager.command
def active_tasks(queue):
    i = celery.control.inspect()
    for tasks in i.active().values():
        for t in tasks:
            if t['delivery_info']['routing_key'] == queue:
                return t
    return ''
