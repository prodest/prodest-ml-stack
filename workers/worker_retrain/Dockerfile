# Template baseado em https://hub.docker.com/_/python/
FROM python:3.11

RUN useradd -m retruser && mkdir /worker_retrain

WORKDIR /worker_retrain
COPY . .

RUN pip install --no-cache-dir --upgrade pip setuptools && pip install --no-cache-dir -r requirements.txt

RUN chown -R retruser:retruser /worker_retrain && chgrp -R 0 /worker_retrain && chmod -R g=u /worker_retrain

USER retruser