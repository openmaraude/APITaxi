# Build variables to override (with docker build --build-arg) to choose the version of dependencies to install:
#
# - API_TAXI_{UTILS,MODELS}_REPO: default https://github.com/openmaraude/APITaxi_xxx
# - API_TAXI_{UTILS,MODELS}_COMMIT: default master
# - API_TAXI_{UTILS,MODELS}: default ${API_TAXI_xx_REPO}/archive/${API_TAXI_xx_COMMIT}.tar.gz
#
# Volumes to mount on run:
#
# - /etc/uwsgi-emperor/vassals: contains uWSGI configuration files
#
# Example of uWSGI configuration file:
#
# $> cat /etc/uwsgi-emperor/vassals/api-taxi.ini
# [uwsgi]
#
# master = true
# processes = 6
# plugin = python3
# module = APITaxi:create_app()
# socket = /share/api-taxi.sock
# stats = /share/api-taxi-stats.sock
#
# Example of run command:
#
# $> docker run -d -v /abs/path/to/api-taxi.ini:/etc/uwsgi-emperor/vassals/api-taxi.ini:ro -v `pwd`/share:/share $(docker build -q --build-arg API_TAXI_UTILS_COMMIT=master .)

FROM debian

RUN apt-get update && apt-get install -y \
  uwsgi \
  python3-pip \
  libpq-dev \
  uwsgi-emperor \
  uwsgi-plugin-python3

# Download dependencies (APITaxi_utils and APITaxi_models) to /code
ARG API_TAXI_UTILS_REPO=https://github.com/openmaraude/APITaxi_utils
ARG API_TAXI_MODELS_REPO=https://github.com/openmaraude/APITaxi_models

ARG API_TAXI_UTILS_COMMIT=master
ARG API_TAXI_MODELS_COMMIT=master

ARG API_TAXI_UTILS=${API_TAXI_UTILS_REPO}/archive/${API_TAXI_UTILS_COMMIT}.tar.gz
ARG API_TAXI_MODELS=${API_TAXI_MODELS_REPO}/archive/${API_TAXI_MODELS_COMMIT}.tar.gz

ADD ${API_TAXI_UTILS} /tmp/APITaxi_utils.tar.gz
ADD ${API_TAXI_MODELS} /tmp/APITaxi_models.tar.gz

RUN mkdir -p /code/APITaxi_utils && tar -xvf /tmp/APITaxi_utils.tar.gz -C /code/APITaxi_utils --strip 1
RUN mkdir -p /code/APITaxi_models && tar -xvf /tmp/APITaxi_models.tar.gz -C /code/APITaxi_models --strip 1

RUN rm -f /tmp/APITaxi_utils.tar.gz
RUN rm -f /tmp/APITaxi_models.tar.gz

# Install dependencies
RUN pip3 install /code/APITaxi_utils
RUN pip3 install /code/APITaxi_models

ADD . /code/APITaxi
RUN pip3 install /code/APITaxi

WORKDIR /code/APITaxi

CMD ["/usr/bin/uwsgi", "--ini", "/etc/uwsgi-emperor/emperor.ini"]
