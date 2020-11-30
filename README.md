# Le.taxi API

API behind [le.taxi](https://le.taxi/).

## Installation

This project has several dependencies:

* PostgreSQL
* celery for asynchronous tasks
* redis as celery backend
* redis as database where taxis' locations are stored
* InfluxDB to store statistics

To setup the API locally, use [APITaxi_devel](https://github.com/openmaraude/APITaxi_devel).

## Unittests

On push, tests are automatically run by cirleci. To run tests locally, assuming you are using APITaxi_devel:

```bash
$> docker-compose exec api bash
api@f4fd953d0667:/git/APITaxi: sudo -H /venv/bin/pip install -ve .[tests]
api@f4fd953d0667:/git/APITaxi: pytest -v -x -s
```

Before tests are executed, a PostgreSQL database is created and alembic migrations are applied. To improve speed, database is kept for subsequent runs in `/tmp/tests_<hash>`. If the database is corrupted because the previous tests run didn't end properly, remove `/tmp/tests_<hash>` and run tests again.

Example of error requiring to remove the database manually:

```
RuntimeError: *** failed to launch Postgresql ***
2020-10-15 08:49:33.269 UTC [1080] FATAL:  lock file "postmaster.pid" already exists
2020-10-15 08:49:33.269 UTC [1080] HINT:  Is another postmaster (PID 1028) running in data directory "/tmp/tests_fa54bbeddf53eb368fd05b9ca121dbc5/data"?
```
