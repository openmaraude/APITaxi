# API Open Data Taxi #
API and Backoffice for taxis' operators and local authorities.

## Pre-requisites ##

 * `Python 2.7`
 * `Alembic` (for the database migration)
 * `Pip`
 * `Postgresql` and `postgresql-dev` (other databases might work)
 * `libspatialindex-dev`
 * `Rabbit-MQ` or `redis`: To queue asynchronous tasks
 * `InfluxDB`: To store views of the taxis activity

We also recommend the use of `virtualenv`

## Initialization ##

### Install Python dependencies ###
Simply run `pip install -r requirements.txt` to install python dependencies 

### Edit the database settings ###
A database has to be created for this project.
The default settings file `default_settings.py` should then be 
edited accordingly (SQLALCHEMY_DATABASE_URI field) and renamed `dev_settings.py`.

### Initialize the database ###
In order to populate the database with the tables and default data, run:
`APITAXI_CONFIG_FILE=APITaxi/dev_settings.py PYTHON_PATH=. manage.py db upgrade head`

### Initialize the InfluxDB database ###
To initialize this database you need to run this command:
`APITAXI_CONFIG_FILE=APITaxi/dev_settings.py PYTHON_PATH=. manage.py create_influx_db

### Add an administrator ###
Just run this command
`APITAXI_CONFIG_FILE=APITaxi/dev_settings.py PYTHON_PATH=. manage.py create_admin your_email@your_domain.com`
type a password.

## Run the server ##

`APITAXI_CONFIG_FILE=APITaxi/dev_settings.py PYTHON_PATH=. manage.py runserver`

## Run taxi's activity storage ##
You can configure in your settings the storage.
`APITAXI_CONFIG_FILE=dev_settings.py celery worker -A celery_worker.celery -B -l info`

you can then access:
* the backoffice here: `http://127.0.0.1:5000/`
* and the API doc here: `http://127.0.0.1:5000/doc`

A wsgi file is also provided if a webserver is required (Apache has been tested, Nginx should work). 
