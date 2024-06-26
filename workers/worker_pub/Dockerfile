# Template baseado em https://hub.docker.com/_/python/
FROM python:3.10

RUN useradd -m pubuser && mkdir /worker_pub

WORKDIR /worker_pub
COPY . .

RUN pip install --no-cache-dir --upgrade pip setuptools && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir pika==1.3.2 requests==2.32.3

RUN chown -R pubuser:pubuser /worker_pub && chgrp -R 0 /worker_pub && chmod -R g=u /worker_pub

USER pubuser
CMD [ "python", "ml_a2edadc4ecb2b9f74bc34.py" ]