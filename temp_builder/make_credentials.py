# --------------------------------------------------------------------------------------------------------------------
# Este script gera credenciais automaticamente para substituir as credenciais padrões dos Dockerfiles e compose files
# da Stack. Essas credenciais são gravadas em um arquivo chamado 'credentials_stack.txt' que é utilizado pelo script
# 'modify_credentials_dockerfiles.sh' para modificar as credenciais.
# --------------------------------------------------------------------------------------------------------------------
import bcrypt
from hashlib import sha256
from time import time
from numpy import random
from jose import jwt
from datetime import datetime

# https://stackoverflow.com/questions/78628938/trapped-error-reading-bcrypt-version-v-4-1-2
bcrypt.__about__ = bcrypt


def generate_hash():
    """
    Gera um hash SHA-256.
        :return: Hash SHA-256 gerado.
    """
    # Gera chave aleatória para incluir no texto a ser passado para gerar o hash
    lst_key_shuffled = list("mwiLCJhZG1pbiI6dHJ1ZSwiaWF0IjoxLjUxNjIzOTAyMjY2MjYzNjRlKzMwfQ.ERCga1Ed2DUPml0b4y03a0TsX"
                            "YRjgSXWsmPyrBl0gFIe7Dr85ddsGDOj3vH2ucdj")
    random.shuffle(lst_key_shuffled)
    key_shuffled = "".join(lst_key_shuffled)

    h = sha256()
    text = str(time()) + str(random.rand()) + key_shuffled + str(random.rand())
    h.update(text.encode('utf-8'))
    return h.hexdigest()


def generate_token():
    """
    Gera um token para acesso à API.
        :return: Token gerado.
    """
    # Gera chave aleatória para incluir no texto a ser passado para gerar o hash
    lst_key_shuffled = list("WNXF1dG80RENaU3dpYVdGMElqb3hMalV4TmpJek9UQXlNajd3OTJ0dkFyR1Ruc09FRllEIiwibmFtZSI6IkpvaG4"
                            "gRG9lIGFzZmFkZmFkZmFzZmQiLCJpYXQiOjE1MTYyMjIzNDMzOTAyMn0.ju_NsELAYqYdET_qtmA9TSFOAnoQ4r"
                            "HrERTuRioctQY")
    random.shuffle(lst_key_shuffled)
    key_shuffled = "".join(lst_key_shuffled)

    # Cria os parâmetros para a geração do token
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    secret_key = pwd_context.hash(str(time()) + str(random.rand()) + key_shuffled + str(random.rand()))
    algorithm = "HS256"
    data = {'system': 'ML API',
            'gen_date': datetime.fromtimestamp(time()).strftime('%d/%m/%Y'),
            'expires': 'never'}

    # Gera o token
    token = jwt.encode(data.copy(), secret_key, algorithm=algorithm)

    return token


def generate_password():
    """
    Gera uma senha.
        :return: Senha gerada.
    """
    pwd_hash = generate_hash()
    enxerto = "ABCDEFGHIJKLMNOPQRSTUVWXYZghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZghijklmnopqrstuvwxyzABCDEFGHI" \
              "JKLMNOPQRSTUVWXYZghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZghijklmnopqrstuvwxyz"
    lst_passwd = list(pwd_hash + enxerto)
    random.shuffle(lst_passwd)
    passwd_shuffled = "".join(lst_passwd[:int(len(pwd_hash)/2)])
    return passwd_shuffled


if __name__ == "__main__":
    from passlib.context import CryptContext
    arq_cred = None

    # Gera as credenciais para o Compose File
    try:
        arq_cred = open("credentials_stack.txt", 'w')
    except PermissionError:
        print(f"\nErro ao criar o arquivo 'credentials_stack.txt'. Permissão de escrita negada!\n")
        exit(1)

    arq_cred.write("# -----------------------------------------------------------------------------------------------"
                   "-----\n")
    arq_cred.write("# ATENÇÃO!!! CADASTRE ESSAS CREDENCIAIS EM UM COFRE DE SENHAS E DESCARTE ESTE ARQUIVO!!!\n#\n")
    arq_cred.write("# NOTA: Essas credenciais mudarão a cada deploy. Mas, apesar de NÃO recomendado,\n")
    arq_cred.write("#       se for preciso manter as mesmas credenciais, é só --NÃO-- apagar o arquivo.\n")
    arq_cred.write("# ------------------------------------------------------------------------------------------------"
                   "----\n\n")

    arq_cred.write("\n# **** CREDENCIAIS PARA ADMINISTRAÇÃO DA STACK (--NÃO PASSAR-- para o SYS ADMIN nem para o "
                   "cientista de dados, pois não são necessárias para eles) ****\n\n")

    # Gera as credenciais que os workers utilizarão ao informar os worker_id e modelos para incluir na lista de filas
    arq_cred.write(f"# ADV_WORKID:\nadvworkid_credential={generate_hash()}\n\n")

    # Gera o token que os workers utilizarão para interagirem com os endpoints de atualização de status e retorno da API
    arq_cred.write(f"# KEY_WORKERS:\nkey_workers={generate_token()}\n\n")

    # MongoDB
    arq_cred.write(f"# Database (MONGODB):\nuser_mongodb=root{generate_hash()[:4]}\npwd_mongodb="
                   f"{generate_password()}\n\n")

    # Minio
    user_minio = f"minuser{generate_hash()[:4]}"
    pwd_minio = f"{generate_password()}"
    arq_cred.write(f"# Storage (MINIO):\nminio_root_user={user_minio}\nminio_root_password={pwd_minio}\n\n")

    # RabbitMQ
    arq_cred.write(f"# Queue (RABBITMQ):\nrabbitmq_default_user=rbquser{generate_hash()[:4]}\n"
                   f"rabbitmq_default_pass={generate_password()}\n\n")

    # Workerid
    arq_cred.write(f"# WORKER_ID_001:\nworker_id_001={generate_hash()}\n\n")

    # Admin do MLFlow
    mlflow_admin_username = f"mlflowadmin{generate_hash()[:4]}"
    mlflow_admin_password = generate_password()
    arq_cred.write(f"# Model Registry (MLFLOW):\nadmin_username={mlflow_admin_username}\n"
                   f"admin_password={mlflow_admin_password}\n\n")
    
    # Secret Key do Flask (framework usado pelo MLFlow)
    secret_key_flask = generate_password()
    arq_cred.write(f"# Secret Key do Flask (framework usado pelo MLFlow):\nsecret_key_flask={secret_key_flask}\n\n")

    # Acesso Minio
    arq_cred.write(f"# ACESSO STORAGE (MINIO) (Obs.: São as mesmas do usuário admin. Se preferir, pode criar outras "
                   f"credenciais, mas lembre-se de dar permissão de escrita no bucket 'mlflow'):\n"
                   f"aws_access_key_id={user_minio}\naws_secret_access_key={pwd_minio}\n\n")

    arq_cred.write("\n# ***** CREDENCIAIS PARA REGISTRO DOS MODELOS DE ML (Passe o bloco de informações abaixo para o "
                   "cientista de dados. --NÃO PASSAR-- para o SYS ADMIN) *****\n\n\n")

    arq_cred.write("# ------------- CIENTISTA DE DADOS: Configure estas variáveis de ambiente no seu computador para "
                   "utilizar o servidor MLflow da stack -------------\n#\n")
    arq_cred.write(f"# MLFLOW_TRACKING_USERNAME={mlflow_admin_username}\n")
    arq_cred.write(f"# MLFLOW_TRACKING_PASSWORD={mlflow_admin_password}\n#\n")

    arq_cred.write("# Assumindo que está rodando localmente, altere 'http://localhost' para o endereço do MLflow, "
                   "observar que pode ser https e outra porta.\n")
    arq_cred.write("# MLFLOW_TRACKING_URI=http://localhost:5000/\n#\n")

    arq_cred.write("# Assumindo que está rodando localmente, altere 'http://localhost' para o endereço do Minio, "
                   "observar que pode ser https e outra porta.\n")
    arq_cred.write("# MLFLOW_S3_ENDPOINT_URL=http://localhost:9000/\n#\n")

    arq_cred.write(f"# AWS_ACCESS_KEY_ID={user_minio}\n")
    arq_cred.write(f"# AWS_SECRET_ACCESS_KEY={pwd_minio}\n#\n")

    arq_cred.write("# ------------------------------------- FIM DO BLOCO DE INFORMAÇÕES PARA O CIENTISTA DE DADOS --"
                   "--------------------------------------------------\n\n")

    arq_cred.write("\n# **************** TOKEN PARA CONSUMIR A API (Passar --SOMENTE-- isso para o SYS ADMIN) *****"
                   "***********\n\n")

    # API Token
    arq_cred.write(f"# API_TOKEN:\napi_token={generate_token()}\n\n")

    arq_cred.write(f"# ---------------------------------------------------------------------------------------------"
                   f"-------\n\n")
    arq_cred.close()
