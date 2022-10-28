FROM python:3.8-buster
MAINTAINER Nick Bolten <nbolten@gmail.com>

ARG GIT_HASH="5fd34abcf855ef51a69d010c421dbb680ebcc128"

ENV SERVER_PORT=5656

RUN apt-get update && \
    apt-get install -y \
      fiona \
      libsqlite3-mod-spatialite

RUN pip install poetry==1.1.8

RUN mkdir -p /install
WORKDIR /install

# TODO: don't use poetry? It's a bit hacky
RUN git clone https://github.com/nbolten/unweaver.git unweaver

WORKDIR /install/unweaver

RUN git checkout $GIT_HASH \
 && poetry install

RUN poetry add osm-humanized-opening-hours \
  && poetry add pytz


CMD ["poetry", "run", "unweaver"]
