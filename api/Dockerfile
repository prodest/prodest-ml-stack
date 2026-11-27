# https://hub.docker.com/_/python/
FROM python:3.12

# Alterar sempre que houver mudança de versões da Stack e/ou da mllibprodest
ENV STACK_VERSION="r1.6.21 (mllibprodest==1.8.14)"

WORKDIR /data
COPY *.py *.sh .

RUN useradd -m apiuser && chmod -R u=rx,g=rx,o=rx /data
RUN pip install --no-cache-dir --upgrade pip==26.3 setuptools==84.2.1 && pip install --no-cache-dir pymongo==4.20.2 requests==2.34.2 \
    numpy==2.5.5 pika==1.5.0 uvicorn==0.54.0 fastapi==0.165.0 pydantic==2.14.4

USER apiuser
ENTRYPOINT ["/bin/bash", "init_app.sh"]