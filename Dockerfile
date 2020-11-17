# Example of uwsgi.ini to mount in /uwsgi.ini:
#
# [uwsgi]
#
# master = true
# processes = 24
# plugin = python3
# module = APITaxi:create_app()
# socket = 0.0.0.0:5000
# stats = 0.0.0.0:5007 --stats-http

FROM ubuntu

ARG API_TAXI_MODELS_URL=https://github.com/openmaraude/APITaxi_models
ARG API_TAXI_MODELS_COMMIT=master

ENV DEBIAN_FRONTEND=noninteractive
ENV DEBCONF_NONINTERACTIVE_SEEN=true

RUN apt-get update && apt-get install -y \
  libpq-dev \
  python3-pip \
  uwsgi \
  uwsgi-plugin-python3

RUN useradd api

# Required by click with Python3, cf https://click.palletsprojects.com/python3/
ENV LC_ALL=C.UTF-8

# Install admin interface
RUN pip3 install flower

# `flask shell` and flask commands like `flask create_user` need FLASK_APP to be set.
ENV FLASK_APP=APITaxi

RUN mkdir -p /var/run/api-taxi
RUN chown api:api /var/run/api-taxi

# ADD detects if file has changed. If we instead ran pip3 install <url>, docker
# would use the cache even if the file has changed.
ADD ${API_TAXI_MODELS_URL}/archive/${API_TAXI_MODELS_COMMIT}.tar.gz /tmp/api_taxi_models.tar.gz
RUN pip3 install /tmp/api_taxi_models.tar.gz
RUN rm -rf /tmp/api_taxi_models.tar.gz

COPY . /app
WORKDIR /app

RUN pip3 install .

USER api

CMD ["uwsgi", "/uwsgi.ini"]
