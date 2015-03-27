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
`BO_OPERATEURS_CONFIG_FILE=backoffice_operateurs/dev_settings.py PYTHON_PATH=. backoffice_operateurs/manage.py db upgrade head`

### Add an administrator ###
Just run this command
`BO_OPERATEURS_CONFIG_FILE=backoffice_operateurs/dev_settings.py PYTHON_PATH=. backoffice_operateurs/manage.py create_admin your_email@your_domain.com`
type a password.

## Run the server ##

`BO_OPERATEURS_CONFIG_FILE=backoffice_operateurs/dev_settings.py PYTHON_PATH=. backoffice_operateurs/manage.py runserver`

you can access the backoffice here: `http://127.0.0.1:5000/ads/`
