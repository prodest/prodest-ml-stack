#!/bin/bash
# --------------------------------------------------------------------------------------------------------------------
# Este script roda dentro do container temporário e gera as credenciais padrões da Stack automaticamente 
# através do script 'make_credentials.py'
# --------------------------------------------------------------------------------------------------------------------
cd temp_builder

# Gera um arquivo de lock para evitar que o deploy continue, caso o usuário cancele
touch lock_builder_iqyvmobtmw4pxi4r0bt.lck

echo "# Início da execução: $(date)" >> log_tempbuilder.txt
echo "" >> log_tempbuilder.txt
echo "# ---> Gerando as configurações das ENV no '.env' utilizado pelo docker-compose..." >> log_tempbuilder.txt
msg_fim=""

# Cria o arquivo com as credenciais, caso não exista
if [ ! -f "credentials_stack.txt" ]; then
       python make_credentials.py
       msg_fim="As credenciais foram geradas com sucesso no arquivo 'temp_builder/credentials_stack.txt'!"
       sleep 2
else
    echo "# >>>>> Utilizando as credenciais já existentes no arquivo 'temp_builder/credentials_stack.txt'" >> log_tempbuilder.txt
    echo "" >> log_tempbuilder.txt
    echo "# >>>>> $(date) - AVISO: Utilizando as credenciais já existentes neste arquivo." >> credentials_stack.txt
    echo ""  >> credentials_stack.txt
    echo "# Caso NÃO queira que as credenciais sejam reaproveitadas, apague este arquivo e faça o deploy novamente!" >> credentials_stack.txt
    echo ""  >> credentials_stack.txt
    echo -e "\n\e[1;32m>>>>> Utilizando as credenciais já existentes no arquivo 'temp_builder/credentials_stack.txt'."
    echo "      Se deseja alterar as credenciais, pressione CTRL+c para abortar o deploy;"
    echo -e "      EXCLUA o arquivo 'temp_builder/credentials_stack.txt' e inicie o deploy novamente.\e[0m\n"
    echo "Se você NÃO cancelar..., o deploy vai continuar automaticamente e irá REAPROVEITAR as credenciais!"
    sleep 30
    echo ""

    printf "%s" 'Continuando em... '
    for i in {9..1}
    do
      printf "%s\b" $i
      sleep 1
    done

    msg_fim="As credenciais foram REAPROVEITADAS do arquivo 'temp_builder/credentials_stack.txt'!"
fi

# Importa o arquivo com as credenciais
source credentials_stack.txt

# Gera as configurações das ENV no '.env' utilizado pelo Compose
echo "- Gerando as credenciais no arquivo '../stack/.env'..." >> log_tempbuilder.txt
echo "MLFLOW_TRACKING_USERNAME=$admin_username" > ../stack/.env
echo "MLFLOW_TRACKING_PASSWORD=$admin_password" >> ../stack/.env
echo "MLFLOW_FLASK_SERVER_SECRET_KEY=$secret_key_flask" >> ../stack/.env
echo "ADVWORKID_CREDENTIAL=$advworkid_credential" >> ../stack/.env
echo "WORKER_ID_001=$worker_id_001" >> ../stack/.env
echo "API_TOKEN=$api_token" >> ../stack/.env
echo "API_TOKEN_WORKERS=$key_workers" >> ../stack/.env
echo "AWS_ACCESS_KEY_ID=$aws_access_key_id" >> ../stack/.env
echo "AWS_SECRET_ACCESS_KEY=$aws_secret_access_key" >> ../stack/.env
echo "RABBITMQ_DEFAULT_USER=$rabbitmq_default_user" >> ../stack/.env
echo "RABBITMQ_DEFAULT_PASS=$rabbitmq_default_pass" >> ../stack/.env
echo "MINIO_ROOT_USER=$minio_root_user" >> ../stack/.env
echo "MINIO_ROOT_PASSWORD=$minio_root_password" >> ../stack/.env
echo "MONGO_INITDB_ROOT_USERNAME=$user_mongodb" >> ../stack/.env
echo "MONGO_INITDB_ROOT_PASSWORD=$pwd_mongodb" >> ../stack/.env

# Gera o arquivo 'mlflow_cred.txt' que é utilizado pelo Model Registry
echo "MLFLOW_TRACKING_USERNAME=$admin_username" > ../model_registry/mlflow_cred.txt
echo "MLFLOW_TRACKING_PASSWORD=$admin_password" >> ../model_registry/mlflow_cred.txt

echo "" >> log_tempbuilder.txt
echo "# Fim da execução." >> log_tempbuilder.txt
echo "" >> log_tempbuilder.txt
echo -e "\n\n"
echo $msg_fim
echo -e "\n-> Elas foram utilizadas para preencher os valores das ENV do compose file da Stack.\n"
rm lock_builder_iqyvmobtmw4pxi4r0bt.lck
sleep 2
