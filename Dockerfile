##### DEV API IMAGE #####

FROM ubuntu:20.04 AS devenv

ENV DEBIAN_FRONTEND=noninteractive
ENV DEBCONF_NONINTERACTIVE_SEEN=true

RUN apt-get install -y gpgv
RUN apt-get update && apt-get install -y \
  git \
  less \
  libffi-dev \
  libgeos-dev \
  libpq-dev \
  python3-pip \
  postgis \
  redis-server \
  sudo \
  vim

RUN pip3 install virtualenv

WORKDIR /git/APITaxi

ADD devenv/entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]

# Create user and add in sudo
RUN useradd api
RUN echo "api ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER api
ENV VIRTUAL_ENV=/venv
ENV PATH=/venv/bin/:$PATH
ENV HOME=/tmp

ENV APITAXI_CONFIG_FILE=/settings.py
ENV FLASK_DEBUG=1
ENV FLASK_APP=APITaxi
CMD ["flask", "run", "--host", "0.0.0.0", "--port", "5000"]


##### DEV WORKER IMAGE #####

FROM devenv AS  worker-devenv

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
# --debug-force-polling is required for mac M1, see https://github.com/gorakhargosh/watchdog/issues/838
CMD watchmedo auto-restart --debug-force-polling --interval=2 --directory=/git/ --pattern='*.py' --recursive -- celery --app=APITaxi2.celery_worker.celery worker -E -c 1


##### DEV WORKER BEAT IMAGE #####

FROM worker-devenv AS worker-beat-devenv

CMD watchmedo auto-restart --debug-force-polling --interval=2 --directory=/git/ --pattern='*.py' --recursive -- celery --app=APITaxi2.celery_worker.celery beat -s /tmp/celerybeat-schedule --pidfile /tmp/celerybeat.pid


##### PROD IMAGE #####
FROM ubuntu:20.04

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
