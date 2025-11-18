# https://hub.docker.com/_/python/
FROM python:3.12

# Alterar sempre que houver mudança de versões da Stack e/ou da mllibprodest
ENV STACK_VERSION="r1.6.17 (mllibprodest==1.8.11)"

WORKDIR /data
COPY *.py *.sh .

RUN useradd -m apiuser && chmod -R u=rx,g=rx,o=rx /data
RUN pip install --no-cache-dir --upgrade pip setuptools && pip install --no-cache-dir pymongo==4.15.4 requests==2.32.5 \
    numpy==2.3.5 pika==1.3.2 uvicorn==0.38.0 fastapi==0.121.2 pydantic==2.12.4

USER apiuser
ENTRYPOINT ["/bin/bash", "init_app.sh"]