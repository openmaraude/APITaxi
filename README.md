# Le.taxi API

API behind [le.taxi](https://le.taxi/).

## Installation

This project has several dependencies:

* PostgreSQL
* celery for asynchronous tasks
* redis as celery backend
* redis as database where taxis' locations are stored

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

## Migrations

Migrations are versioned with alembic. To run migrations locally using the "api" container from APITaxi_devel, run the following commands:

```
# Connect to api container
$> docker-compose exec api bash

# Change directory to migrations directory
$> cd APITaxi_models2

# Run alembic commands: view current migration
$> alembic current

# Create a new revision file
$> alembic revision --autogenerate -m 'New revision'

# Apply migrations
$> alembic upgrade head
```

To apply migrations to production, connect with ssh to the PostgreSQL master server (taxis01.api.taxi or dev01.api.taxi as specified by [APITaxi_deploy](https://github.com/openmaraude/APITaxi_deploy)), then:

```
# Connect to api container
$> docker exec -ti api_taxi bash

# Change directory to migrations directory
$> cd APITaxi_models2

# Run alembic commands
$> alembic current
$> alembic upgrade head
```

## Production

To deploy to production, setup the following remote and push on the master branches.

```
git remote add clever-dev git+ssh://git@push-n2-par-clevercloud-customers.services.clever-cloud.com/app_89d4b1b8-08db-4e3c-9bb6-07fd2e48ff71.git
git remote add clever-prod git+ssh://git@push-n2-par-clevercloud-customers.services.clever-cloud.com/app_75718459-4a50-4386-a57a-a4e6a841e962.git
```

To connect to containers, install [CleverCloud CLI](https://www.clever-cloud.com/doc/reference/clever-tools/getting_started/) and run the following commands:

```
clever link app_75718459-4a50-4386-a57a-a4e6a841e962
clever link app_89d4b1b8-08db-4e3c-9bb6-07fd2e48ff71

# Outputs "dev-api" and "prod-api"
clever applications

clever ssh -a dev-api
clever ssh -a prod-api
```
