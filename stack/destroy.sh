#!/bin/bash
echo -e "\n\n---------------------------> D E S T R O Y I N G    T H E    S T A C K <---------------------------\n\n"
echo -e "*** ATENÇÃO: Este script irá destruir os containers e apagar as imagens criadas na build/deploy da stack. ***\n"
read -e -p "    >> Deseja continuar [yes/no]? " resp

if [ "${resp}" == "yes" ]
then
    echo -e "\n>>> Destruindo os containers...\n"
    ./docker-compose images -q > images.txt
    ./docker-compose down
    echo -e "\n>>> Apagando as imagens...\n"
    cat images.txt | xargs -r -n 1 docker image rm
    rm -f images.txt
    echo -e "\n\nProcesso de destroy dos containers finalizado.\n\n"

    read -e -p "    >> Deseja destruir o PORTAINER também [yes/no]? " resp

    if [ "${resp}" == "yes" ]
    then
        echo -e "\n>>> Destruindo o Portainer...\n"
        docker stop portainer_4a75ef64b5
        docker rm portainer_4a75ef64b5
        echo -e "\n>>> Apagando o volume do Portainer...\n"
        docker volume rm portainer_data_4a75ef64b5
        echo -e "\n>>> Apagando a imagem do Portainer...\n"
        docker image rm portainer/portainer-ce:latest
        echo -e "\n\nProcesso de destroy do Portainer finalizado.\n\n"
    fi
fi
