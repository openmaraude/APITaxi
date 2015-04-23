# Backoffice operators #
Backoffice for taxis' operators and public administrative workers.œ

## Pre-requisites ##

You need to have on your machine:
 * Python2.7
 * Alembic (for the database migration)
 * Pip
 * Postgresql and postgresql-dev, other databases should work

It's better if you work with virtualenv

## Initialization ##

### Python dependencies ###
You need to run `pip install -r requirements.txt` to install python dependencies 

### Edit settings ###
Please create a database for this project.
Now you need to edit settings, copy `default_settings.py` file in
 `dev_settings.py, edit SQLALCHEMY_DATABASE_URI field in `dev_settings.py`.

### Database initialization ###
You can populate your database with the tables and default data, just run :
`APITAXI_CONFIG_FILE=APITaxi/dev_settings.py PYTHON_PATH=. manage.py db upgrade head`

### Add an administrator ###
Just run this command
`APITAXI_CONFIG_FILE=APITaxi/dev_settings.py PYTHON_PATH=. manage.py create_admin your_email@your_domain.com`
type a password.

## Run the server ##

`APITAXI_CONFIG_FILE=APITaxi/dev_settings.py PYTHON_PATH=. manage.py runserver`

you can access the backoffice here: `http://127.0.0.1:5000/ads/`
