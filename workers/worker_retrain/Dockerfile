# Template retirado de https://hub.docker.com/_/python/
FROM python:3.10

WORKDIR /worker_retrain
COPY . .

RUN useradd -m retruser && chown -R retruser:retruser /worker_retrain
RUN pip install --no-cache-dir --upgrade pip setuptools && pip install --no-cache-dir -r requirements.txt

USER retruser