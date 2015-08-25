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

you can then access:
* the backoffice here: `http://127.0.0.1:5000/`
* and the API doc here: `http://127.0.0.1:5000/doc`

A wsgi file is also provided if a webserver is required (Apache has been tested, Nginx should work). 


## Run taxi's activity storage ##
 There are two unix services to install & run to store taxis' activity, one sending beats,
 another waiting for beats and interpreting them. This worker will also be able to run
 asynchronous tasks.

 To install these services you need to copy:
  * scripts/celeryd in /etc/init.d/taxis_worker
  * scripts/celerybeat in /etc/init.d/activity_beat

Then you need to edit scripts/example/conf to stick with your configuration (you might
need to create a celery user).
Copy this file in:
  * /etc/default/taxis_worker
  * /etc/default/activity_beat

 Now you should be able to run services with:
  * service taxis_worker start
  * service activity_beat start

