# https://hub.docker.com/_/python/
FROM python:3.12

# Alterar sempre que houver mudança de versões da Stack e/ou da mllibprodest
ENV STACK_VERSION="r1.6.19 (mllibprodest==1.8.13)"

WORKDIR /data
COPY *.py *.sh .

RUN useradd -m apiuser && chmod -R u=rx,g=rx,o=rx /data
RUN pip install --no-cache-dir --upgrade pip==26.2 setuptools==83.0.0 && pip install --no-cache-dir pymongo==4.17.0 requests==2.34.2 \
    numpy==2.5.1 pika==1.4.2 uvicorn==0.52.0 fastapi==0.141.1 pydantic==2.13.4

USER apiuser
ENTRYPOINT ["/bin/bash", "init_app.sh"]