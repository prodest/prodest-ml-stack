# https://hub.docker.com/_/python/
FROM python:3.11

# Alterar sempre que houver mudança de versões da Stack e/ou da mllibprodest
ENV STACK_VERSION="r1.6.14 (mllibprodest==1.8.8)"

WORKDIR /data
COPY *.py *.sh .

RUN useradd -m apiuser && chmod -R u=rx,g=rx,o=rx /data
RUN pip install --no-cache-dir --upgrade pip setuptools && pip install --no-cache-dir pymongo==4.12.0 requests==2.32.3 \
    numpy==2.2.4 pika==1.3.2 uvicorn==0.34.1 fastapi==0.115.12 pydantic==2.11.3

USER apiuser
ENTRYPOINT ["/bin/bash", "init_app.sh"]