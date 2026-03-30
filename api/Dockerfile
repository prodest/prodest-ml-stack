# https://hub.docker.com/_/python/
FROM python:3.12

# Alterar sempre que houver mudança de versões da Stack e/ou da mllibprodest
ENV STACK_VERSION="r1.6.18 (mllibprodest==1.8.12)"

WORKDIR /data
COPY *.py *.sh .

RUN useradd -m apiuser && chmod -R u=rx,g=rx,o=rx /data
RUN pip install --no-cache-dir --upgrade pip==26.0.1 setuptools==82.0.1 && pip install --no-cache-dir pymongo==4.16.0 requests==2.33.1 \
    numpy==2.4.4 pika==1.3.2 uvicorn==0.42.0 fastapi==0.135.2 pydantic==2.12.5

USER apiuser
ENTRYPOINT ["/bin/bash", "init_app.sh"]