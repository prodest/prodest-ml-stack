# https://hub.docker.com/_/python/
FROM python:3.10

# Alterar sempre que houver mudança de versões da Stack e/ou da mllibprodest
ENV STACK_VERSION="r1.6.7 (mllibprodest==1.8.4)"

WORKDIR /data
COPY *.py .

RUN useradd -m apiuser && chmod -R u=rx,g=rx,o=rx /data
RUN pip install --no-cache-dir --upgrade pip setuptools && pip install --no-cache-dir pymongo==4.6.2 requests==2.31.0 \
    numpy==1.26.4 pika==1.3.2 uvicorn==0.28.0 fastapi==0.110.0 pydantic==2.6.4

USER apiuser
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--reload"]
