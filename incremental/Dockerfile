FROM python:3.8-buster
MAINTAINER Nick Bolten <nbolten@gmail.com>

RUN mkdir /app
WORKDIR /app
COPY . /app
RUN pip install -r /app/requirements.txt
RUN pip install .
ENTRYPOINT incremental
