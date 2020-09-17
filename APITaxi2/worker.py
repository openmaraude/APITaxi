from flask import current_app


@current_app.celery.task(name='toto')
def toto():
    print('xxxxxxxxxxxx')
