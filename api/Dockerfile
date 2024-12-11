# https://hub.docker.com/_/python/
FROM python:3.10

# Alterar sempre que houver mudança de versões da Stack e/ou da mllibprodest
ENV STACK_VERSION="r1.6.13 (mllibprodest==1.8.7)"

WORKDIR /data
COPY *.py *.sh .

RUN useradd -m apiuser && chmod -R u=rx,g=rx,o=rx /data
RUN pip install --no-cache-dir --upgrade pip setuptools && pip install --no-cache-dir pymongo==4.10.1 requests==2.32.3 \
    numpy==2.1.2 pika==1.3.2 uvicorn==0.31.0 fastapi==0.115.0 pydantic==2.9.2

USER apiuser
ENTRYPOINT ["/bin/bash", "init_app.sh"]