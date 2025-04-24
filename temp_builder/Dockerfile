# Utilizado para gerar uma imagem para um container temporário que gera as credenciais usadas no build/deploy dos
# containers da stack
# https://hub.docker.com/_/python/
FROM python:3.11

WORKDIR prodest-ml-stack
RUN pip install --no-cache-dir --upgrade pip setuptools && pip install --no-cache-dir numpy==2.2.4 "python-jose[cryptography]==3.4.0" "passlib[bcrypt]==1.7.4"

CMD ["/bin/bash", "temp_builder/modify_credentials_dockerfiles.sh"]
