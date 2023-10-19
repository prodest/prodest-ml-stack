#!/bin/bash

# Cria o arquivo com o novo signup
python /tmp/make_signup.py
sleep 2

# Importa o arquivo com o novo signup
source /tmp/url_signup.txt

# Importa o arquivo com as credenciais do MLflow
source /tmp/mlflow_cred.txt

# Substituindo as configurações default do admin do MLFlow
sed -i "s/admin_username[[:space:]]=[[:space:]]admin/admin_username = $MLFLOW_TRACKING_USERNAME/" $PY_INST_DIR/mlflow/server/auth/basic_auth.ini
sed -i "s/admin_password[[:space:]]=[[:space:]]password/admin_password = $MLFLOW_TRACKING_PASSWORD/" $PY_INST_DIR/mlflow/server/auth/basic_auth.ini

# Substituindo a rota de signup do MLFlow para evitar o cadastro de usuários por lá
sed -i "s/SIGNUP[[:space:]]=[[:space:]]\"\/signup\"/SIGNUP = \"\/$signup_new\"/" $PY_INST_DIR/mlflow/server/auth/routes.py

# Faz uma limpeza...
rm /tmp/make_signup.py
rm /tmp/url_signup.txt
rm /tmp/mlflow_cred.txt
