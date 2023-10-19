# Template retirado de https://hub.docker.com/_/python/
FROM python:3.10

WORKDIR /training_model
COPY . .

RUN useradd -m trainuser && chown -R trainuser:trainuser /training_model && apt-get update && \
    apt-get install -y nano && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --upgrade pip setuptools && pip install --no-cache-dir -r requirements.txt

USER trainuser