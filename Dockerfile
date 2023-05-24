##### DEV API IMAGE #####

# Timescale is required for tests, it's based on Ubuntu 22.04
FROM timescale/timescaledb-ha:pg14-ts2.8-oss-latest AS base-devenv

ENV DEBIAN_FRONTEND=noninteractive
ENV DEBCONF_NONINTERACTIVE_SEEN=true

USER root
RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y gpgv
RUN apt-get install -y \
  git \
  less \
  gcc \
  libffi-dev \
  libgeos-dev \
  libpq-dev \
  python3-dev \
  python3-pip \
  redis-server \
  sudo \
  vim


##### DEV TEST IMAGE #####

FROM base-devenv AS test-devenv

RUN pip3 install tox

USER postgres

ENTRYPOINT ["/usr/bin/bash"]


#### DEV API IMAGE #####

FROM base-devenv AS devenv

RUN pip3 install virtualenv

WORKDIR /git/APITaxi

ADD devenv/entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]

# needed to run "sudo -E /venv/bin/pip install"
RUN echo "postgres ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# timescaledb-ha already creates a user with uid 1000, and the development environment
# assumes you are also uid 1000 so both can read and write code
# we used to create a user "api", now it's "postgres"
USER postgres
ENV VIRTUAL_ENV=/venv
ENV PATH=/venv/bin/:$PATH
ENV HOME=/tmp

ENV APITAXI_CONFIG_FILE=/settings.py
CMD ["flask", "run", "--debug", "--app", "APITaxi", "--host", "0.0.0.0", "--port", "5000"]


##### DEV WORKER IMAGE #####

FROM devenv AS worker-devenv

USER root
RUN useradd worker
RUN echo "worker ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER worker
ENV VIRTUAL_ENV=/venv
ENV PATH=/venv/bin/:$PATH
ENV APITAXI_CONFIG_FILE=/settings.py

# If we use the square bracket CMD style, process doesn't auto-reload on code change.
# The simple CMD format is used on purpose, until we understand why CMD [...] doesn't work.
#
# --debug-force-polling with an interval would be required for Mac M1, see https://github.com/gorakhargosh/watchdog/issues/838
CMD watchmedo auto-restart --directory=/git/ --pattern='*.py' --recursive -- celery --app=APITaxi2.celery_worker worker -E -c 1


##### DEV WORKER BEAT IMAGE #####

FROM worker-devenv AS worker-beat-devenv

# Same comment as above for Mac M1
CMD watchmedo auto-restart --directory=/git/ --pattern='*.py' --recursive -- celery --app=APITaxi2.celery_worker beat -s /tmp/celerybeat-schedule --pidfile /tmp/celerybeat.pid


##### PROD IMAGE #####
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DEBCONF_NONINTERACTIVE_SEEN=true

RUN apt-get update && apt-get install -y \
  libpq-dev \
  python3-pip \
  libgeos-dev \
  supervisor \
  less

RUN useradd api

# Required by click with Python3, cf https://click.palletsprojects.com/python3/
ENV LC_ALL=C.UTF-8

# Install admin interface
RUN pip3 install uwsgi flower

# `flask shell` and flask commands like `flask create_user` need FLASK_APP to be set.
ENV FLASK_APP=APITaxi

RUN mkdir -p /var/run/api-taxi
RUN chown api:api /var/run/api-taxi

# COPY setup.py first before running `pip3 install .` to use Docker cache if
# dependencies did not change. APITaxi/__init__.py is read by setup.py, so it
# is also required.
COPY setup.py /app/
COPY APITaxi/__init__.py /app/APITaxi/
WORKDIR /app

RUN pip3 install .

# Supervisor and services configuration
COPY deploy/supervisor/* /etc/supervisor/conf.d/
COPY deploy/conf/* /etc/api-taxi/

# Application source code
COPY . /app

CMD ["/usr/bin/supervisord", "--nodaemon"]
