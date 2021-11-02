FROM python:3.9.7-slim-bullseye AS base_stage_app_svc
COPY . /opt/startup
WORKDIR /opt/startup
RUN chmod 744 wait-for-it.sh; chmod 744 startup.sh
RUN apt-get update && apt-get -y install postgresql
RUN pip install --upgrade pip