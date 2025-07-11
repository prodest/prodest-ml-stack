# https://hub.docker.com/_/python/
FROM python:3.11

# Alterar sempre que houver mudança de versões da Stack e/ou da mllibprodest
ENV STACK_VERSION="r1.6.15 (mllibprodest==1.8.9)"

WORKDIR /data
COPY *.py *.sh .

RUN useradd -m apiuser && chmod -R u=rx,g=rx,o=rx /data
RUN pip install --no-cache-dir --upgrade pip setuptools && pip install --no-cache-dir pymongo==4.13.2 requests==2.32.4 \
    numpy==2.3.1 pika==1.3.2 uvicorn==0.35.0 fastapi==0.116.0 pydantic==2.11.7

USER apiuser
ENTRYPOINT ["/bin/bash", "init_app.sh"]