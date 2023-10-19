# https://hub.docker.com/_/python/
FROM python:3.10

# Alterar sempre que houver mudança de versões da Stack e/ou da mllibprodest
ENV STACK_VERSION="r1.6.0 (mllibprodest==1.8.0)"

WORKDIR /data
COPY *.py .

RUN useradd -m apiuser && chmod -R u=rx,g=rx,o=rx /data
RUN pip install --no-cache-dir --upgrade pip setuptools && pip install --no-cache-dir pymongo==4.5.0 requests==2.31.0 \
    numpy==1.26.0 pika==1.3.2 uvicorn==0.23.2 fastapi==0.95.2

USER apiuser
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--reload"]
