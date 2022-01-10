#!/bin/sh

# If the directory /venv/ is empty, fill it with a new virtualenv. /venv can be
# mounted as a docker volume to persist packages installation.
sudo -E find /venv/ -maxdepth 0 -empty -exec virtualenv /venv \;

. /venv/bin/activate

sudo -E /venv/bin/pip install flower tox watchdog[watchmedo] pytest flake8 pylint

test -d "/git/APITaxi" && sudo -E /venv/bin/pip install -e "/git/APITaxi"

# Execute Docker CMD
exec "$@"
