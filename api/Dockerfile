# https://hub.docker.com/_/python/
FROM python:3.10

# Alterar sempre que houver mudança de versões da Stack e/ou da mllibprodest
ENV STACK_VERSION="r1.6.11 (mllibprodest==1.8.6)"

WORKDIR /data
COPY *.py *.sh .

RUN useradd -m apiuser && chmod -R u=rx,g=rx,o=rx /data
RUN pip install --no-cache-dir --upgrade pip setuptools && pip install --no-cache-dir pymongo==4.7.3 requests==2.32.3 \
    numpy==2.0.0 pika==1.3.2 uvicorn==0.30.1 fastapi==0.111.0 pydantic==2.7.4

USER apiuser
ENTRYPOINT ["/bin/bash", "init_app.sh"]