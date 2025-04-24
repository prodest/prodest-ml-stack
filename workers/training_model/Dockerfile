# Template baseado em https://hub.docker.com/_/python/
FROM python:3.11

RUN useradd -m trainuser && mkdir /training_model && apt-get update && apt-get install -y nano && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /training_model
COPY . .

RUN pip install --no-cache-dir --upgrade pip setuptools && pip install --no-cache-dir -r requirements.txt

RUN chown -R trainuser:trainuser /training_model && chgrp -R 0 /training_model && chmod -R g=u /training_model

USER trainuser