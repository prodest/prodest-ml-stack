#!/bin/bash
echo -e "\n\n---------------------------> D E P L O Y I N G    T H E    S T A C K <---------------------------\n"

if [ -f "temp_builder/lock_builder_iqyvmobtmw4pxi4r0bt.lck" ]
then
    echo -e "\n\e[1;31m-------------------------------------- DEPLOY TRAVADO --------------------------------------------------"
    echo "O deploy está travado porque foi cancelado (CTRL+c) na rotina de geração e substituição das credenciais."
    echo "Se foi cancelado para remover o arquivo de credenciais 'temp_builder/credentials_stack.txt', remova-o."
    echo -e "Remova também o arquivo 'temp_builder/lock_builder_iqyvmobtmw4pxi4r0bt.lck' e inicie novamente o deploy.\e[0m\n"
    exit 1
fi

base_path=$(pwd)
repo=https://github.com/prodest/modelo-teste.git
docker_composer_name=docker-compose-linux-x86_64
url_docker_compose=https://github.com/docker/compose/releases/download/v2.20.3/$docker_composer_name

if [ ! -f "$base_path/stack/docker-compose" ]; then
    echo -e ">>> Baixando o Docker Compose...\n"
    cd $base_path/stack
    rm -v $docker_composer_name 2> /dev/null  # Para evitar problemas quando o Download é abortado
    wget -nc $url_docker_compose

    if [ $? -ne 0 ]; then
        echo -e "\n\e[1;31mERRO: Não foi possível obter o Docker Compose através da URL '$url_docker_compose'. Verifique as mensagens acima para mais detalhes.\e[0m\n"
        exit 1
    fi

    cd $base_path
    mv $base_path/stack/$docker_composer_name $base_path/stack/docker-compose
    chmod +x $base_path/stack/docker-compose
fi

echo -e ""
read -e -p "*** ATENÇÃO: Deseja clonar e utilizar o modelo de exemplo ($repo) [yes/no]? " resp

if [ "${resp}" == "yes" ]
then
    echo -e "\n>>> Clonando o repositório com o modelo de exemplo...\n"
    git clone $repo

    if [ $? -ne 0 ]; then
        echo -e "\n\e[1;31mERRO: Falha ao clonar o repositório '$repo'. Verifique as mensagens acima para mais detalhes.\e[0m\n"
        exit 1
    fi

    echo -e "\n>>> Retirando informações de GIT da pasta com o modelo de exemplo...\n"
    rm -vfR $base_path/modelo-teste/.git
    echo -e "\n>>> Copiando a pasta publicar para a pasta principal da Stack...\n"
    cp -vR $base_path/modelo-teste/publicar $base_path
else
    echo -e "\n>>> Utilizando a pasta 'publicar'..."
    echo -e "\n\n            \e[1;31m****** Caso existam arquivos de deploys anteriores, estes serão EXCLUÍDOS! ******\e[0m\n"
    echo -e "\n*** ATENÇÃO: Antes de continuar, copie a pasta 'publicar' do seu modelo para a pasta '$base_path'.\n"
    read -e -p "    A pasta 'publicar' foi copiada? Deseja continuar [yes/no]? " resp
fi

if [ "${resp}" != "yes" ]
then
    echo -e "\nScript abortado!\n"
    exit 1
fi

if [ -d "$base_path/publicar" ]
then
    if [ -d ".git" ]; then
        echo -e "\n>>> Retirando informações de GIT da pasta prodest-ml-stack...\n"
        rm -vfR .git
    fi

    # Verifica se algumas pastas necessárias estão presentes
    pastas_ausentes=""

    if [ ! -d "$base_path/publicar/training_model" ]; then
        pastas_ausentes=$pastas_ausentes"training_model "
    fi

    if [ ! -d "$base_path/publicar/worker_pub/models" ]; then
        pastas_ausentes=$pastas_ausentes"worker_pub/models "
    fi

    if [ ! -d "$base_path/publicar/worker_retrain/models" ]; then
        pastas_ausentes=$pastas_ausentes"worker_retrain/models"
    fi

    if [ "${pastas_ausentes}" != "" ]; then
        echo -e "\n\e[1;31mERRO: Estas pastas NÃO foram encontradas dentro da pasta 'publicar': $pastas_ausentes\e[0m\n"
        exit 1
    fi

    # Verifica se alguns arquivos necessários estão presentes
    arquivos_ausentes=""

    if [ ! -f "$base_path/publicar/training_model/train.py" ]; then
        arquivos_ausentes=$arquivos_ausentes"training_model/train.py "
    fi

    if [ ! -f "$base_path/publicar/worker_pub/params.conf" ]; then
        arquivos_ausentes=$arquivos_ausentes"worker_pub/params.conf "
    fi

    if [ ! -f "$base_path/publicar/worker_retrain/params.conf" ]; then
        arquivos_ausentes=$arquivos_ausentes"worker_retrain/params.conf "
    fi

    if [ ! -f "$base_path/publicar/training_model/requirements.txt" ]; then
        arquivos_ausentes=$arquivos_ausentes"training_model/requirements.txt "
    fi

    if [ ! -f "$base_path/publicar/worker_pub/requirements.txt" ]; then
        arquivos_ausentes=$arquivos_ausentes"worker_pub/requirements.txt "
    fi

    if [ ! -f "$base_path/publicar/worker_retrain/requirements.txt" ]; then
        arquivos_ausentes=$arquivos_ausentes"worker_retrain/requirements.txt"
    fi

    if [ "${arquivos_ausentes}" != "" ]; then
        echo -e "\n\e[1;31mERRO: Estes arquivos NÃO foram encontrados dentro da pasta 'publicar': $arquivos_ausentes\e[0m\n"
        exit 1
    fi

    if [ -d "$base_path/workers_deploy" ]; then
        echo -e "\n>>> Removendo arquivos de deploys anteriores da pasta 'workers'...\n"
        rm -vfR $base_path/workers_deploy
    fi

    echo -e "\n\n>>> Copiando os arquivos necessários para as devidas pastas...\n"
    mkdir $base_path/workers_deploy
    cp -vR $base_path/publicar/training_model $base_path/workers_deploy/
    cp -vR $base_path/publicar/worker_pub $base_path/workers_deploy/
    cp -vR $base_path/publicar/worker_retrain $base_path/workers_deploy/
    cp -v $base_path/workers/worker_pub/ml_a2edadc4ecb2b9f74bc34.py $base_path/workers_deploy/worker_pub/
    cp -v $base_path/workers/worker_retrain/retrain_46b1c135cdef278ddc3b2.py $base_path/workers_deploy/worker_retrain/
    cp -v $base_path/workers/training_model/Dockerfile $base_path/workers_deploy/training_model
    cp -v $base_path/workers/worker_pub/Dockerfile $base_path/workers_deploy/worker_pub
    cp -v $base_path/workers/worker_retrain/Dockerfile $base_path/workers_deploy/worker_retrain

    cd $base_path/temp_builder
    ./make_tempbuilder.sh

    # Interrompe se ocorrer um erro no script 'make_tempbuilder.sh', mas evita que saia quando o usuário faz um
    # CTRL+c para cancelar o deploy
    if [ $? -ne 0 ] && [ ! -f "lock_builder_iqyvmobtmw4pxi4r0bt.lck" ]; then
        exit 1
    fi

    if [ -f "lock_builder_iqyvmobtmw4pxi4r0bt.lck" ]; then
        echo -e "\n\e[1;31m-------------------------------------- DEPLOY TRAVADO --------------------------------------------------"
        echo "O deploy está travado porque foi cancelado (CTRL+c) na rotina de geração e substituição das credenciais."
        echo "Se foi cancelado para remover o arquivo de credenciais 'temp_builder/credentials_stack.txt', remova-o."
        echo -e "Remova também o arquivo 'temp_builder/lock_builder_iqyvmobtmw4pxi4r0bt.lck' e inicie novamente o deploy.\e[0m\n"
        exit 1
    fi

    echo -e "\n\n>>> Construindo as imagens...\n"

    echo -e "\n\n\n\n    [1/5]  * python-training-model *\n\n\n"
    cd $base_path/workers_deploy/training_model
    docker build -t python-training-model . --no-cache

    if [ $? -ne 0 ]; then
        echo -e "\n\e[1;31mERRO: Falha na build da imagem. Verifique as mensagens acima para mais detalhes.\e[0m\n"
        exit 1
    fi

    echo -e "\n\n\n\n    [2/5]  * python-worker *\n\n\n"
    cd $base_path/workers_deploy/worker_pub
    docker build -t python-worker . --no-cache

    if [ $? -ne 0 ]; then
        echo -e "\n\e[1;31mERRO: Falha na build da imagem. Verifique as mensagens acima para mais detalhes.\e[0m\n"
        echo -e "\n>>> Removendo imagens não utilizadas no deploy...\n"
        docker image rm python-training-model
        echo ""
        exit 1
    fi

    echo -e "\n\n\n\n    [3/5]  * python-retrain *\n\n\n"
    cd $base_path/workers_deploy/worker_retrain
    docker build -t python-retrain . --no-cache

    if [ $? -ne 0 ]; then
        echo -e "\n\e[1;31mERRO: Falha na build da imagem. Verifique as mensagens acima para mais detalhes.\e[0m\n"
        echo -e "\n>>> Removendo imagens não utilizadas no deploy...\n"
        docker image rm python-training-model python-worker
        echo ""
        exit 1
    fi

    echo -e "\n\n\n\n    [4/5]  * python-api *\n\n\n"
    cd $base_path/api
    docker build -t python-api . --no-cache

    if [ $? -ne 0 ]; then
        echo -e "\n\e[1;31mERRO: Falha na build da imagem. Verifique as mensagens acima para mais detalhes.\e[0m\n"
        echo -e "\n>>> Removendo imagens não utilizadas no deploy...\n"
        docker image rm python-training-model python-worker python-retrain
        echo ""
        exit 1
    fi

    echo -e "\n\n\n\n    [5/5]  * python-mlflow *\n\n\n"
    cd $base_path/model_registry
    docker build -t python-mlflow . --no-cache

    if [ $? -ne 0 ]; then
        echo -e "\n\e[1;31mERRO: Falha na build da imagem. Verifique as mensagens acima para mais detalhes.\e[0m\n"
        echo -e "\n>>> Removendo imagens não utilizadas no deploy...\n"
        docker image rm python-training-model python-worker python-retrain python-api
        echo ""
        exit 1
    fi

    echo -e "\n\n\n\n>>> Subindo a stack...\n"
    cd $base_path/stack
    ./docker-compose up -d --build

    if [ $? -ne 0 ]; then
        echo -e "\n\e[1;31mERRO: Falha ao tentar subir a stack. Verifique as mensagens acima para mais detalhes.\e[0m\n"
        echo -e "\n>>> Removendo imagens não utilizadas no deploy...\n"
        docker image rm python-training-model python-worker python-retrain python-api python-mlflow
        echo ""
        exit 1
    fi

    sleep 2

    echo -e "\n\n\n\n>>> Parando os containers de treino/retreino do modelo (economia de recursos)...\n"
    docker stop stack-mltraining-model-1
    docker stop stack-worker-retrain-1

    echo -e "\n\n\e[1;32mProcesso de build/deploy finalizado.\e[0m\n\n"
else
    echo -e "\n\e[1;31mERRO: A pasta 'publicar' não foi encontrada no caminho '$base_path'. Script abortado!\e[0m\n"
    exit 1
fi
