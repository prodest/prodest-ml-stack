#!/bin/bash
# --------------------------------------------------------------------------------------------------------------------
# Constrói, utiliza e destrói o container temporário responsável por gerar as credenciais da Stack automaticamente
# --------------------------------------------------------------------------------------------------------------------
echo -e "\n>>> Substituindo as configurações das ENV no arquivo Compose...\n"
echo -e "  *** Fazendo build/deploy de um container temporário para executar esta atividade... ***\n"
cd ..
caminho=${PWD}
cd temp_builder

# Constrói a imagem
docker build -t img-tempbuilder-iqyvmobtmqlijfkzkpzusdw4pxi4r0bt . --no-cache

if [ $? -ne 0 ]; then
    echo -e "\n\e[1;31mERRO: Falha na build da imagem. Verifique as mensagens acima para mais detalhes.\e[0m\n"
    exit 1
fi

sleep 2

# Cria o container
docker run -it -v $caminho:/prodest-ml-stack --name cont-tempbuilder-iqyvmobtmqlijfkzkpzusdw4pxi4r0bt img-tempbuilder-iqyvmobtmqlijfkzkpzusdw4pxi4r0bt

# Evita que a mensagem de erro seja mostrada quando o usuário faz um CTRL+c para cancelar o deploy
if [ $? -ne 0 ] && [ ! -f "lock_builder_iqyvmobtmw4pxi4r0bt.lck" ]; then
      echo -e "\n\e[1;31mERRO: Falha ao tentar criar o container. Verifique as mensagens acima para mais detalhes.\e[0m\n"
      echo -e "\n>>> Removendo a imagem do container temporário: img-tempbuilder-iqyvmobtmqlijfkzkpzusdw4pxi4r0bt"
      docker image rm img-tempbuilder-iqyvmobtmqlijfkzkpzusdw4pxi4r0bt
      echo ""
      exit 1
fi

# Faz uma limpeza...
echo -e "\n>>> Removendo o container temporário: cont_tempbuilder_iqyvmobtmqlijfkzkpzusdw4pxi4r0bt..."
docker rm cont-tempbuilder-iqyvmobtmqlijfkzkpzusdw4pxi4r0bt

echo -e "\n>>> Removendo a imagem do container temporário: img-tempbuilder-iqyvmobtmqlijfkzkpzusdw4pxi4r0bt"
docker image rm img-tempbuilder-iqyvmobtmqlijfkzkpzusdw4pxi4r0bt
echo ""