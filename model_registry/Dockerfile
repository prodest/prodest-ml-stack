# https://hub.docker.com/_/python/
FROM python:3.12

# Pasta onde o Python será instalado. Ao alterar a versão do Python neste Dockerfile, lembre-se de alterar a versão
# nesta variável de ambiente também
ENV PY_INST_DIR=/usr/local/lib/python3.12/site-packages

WORKDIR /tmp
COPY modify_conf_mlflow.sh make_signup.py mlflow_cred.txt .

RUN pip install --no-cache-dir --upgrade pip==26.0.1 setuptools==82.0.1 && pip install --no-cache-dir mlflow[auth]==3.10.1 boto3==1.42.78 \
    numpy==2.4.4 && /tmp/modify_conf_mlflow.sh && rm /tmp/modify_conf_mlflow.sh

WORKDIR /usr/local/bin
COPY mlflow_init.sh .

WORKDIR /mlflow_data
RUN useradd -m mlfuser && chown -R mlfuser:mlfuser /mlflow_data

USER mlfuser
ENTRYPOINT ["/bin/bash", "mlflow_init.sh"]