# Template retirado de https://hub.docker.com/_/python/
FROM python:3.10

WORKDIR /worker_pub
COPY . .

RUN useradd -m pubuser && chown -R pubuser:pubuser /worker_pub
RUN pip install --no-cache-dir --upgrade pip setuptools && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir pika==1.3.2 requests==2.31.0

USER pubuser
CMD [ "python", "ml_a2edadc4ecb2b9f74bc34.py" ]
