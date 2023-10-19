#!/bin/bash
# Teste rápido do endpoint 'inference' do modelo de teste 'CLF_CYBER_BULLYING_TWEETS'

# Altere conforme a variável 'api_token' que consta no arquivo 'temp_builder/credentials_stack.txt'
API_TOKEN="COLE_AQUI_O_TOKEN"

# Intervalo entre cada requisição em segundos
DELAY=0.5

# Contabiliza a quantidade de requisições enviadas
COUNTER=0

while true
do
    curl -X 'POST' \
      'http://localhost:8080/inference' \
      -H 'accept: application/json' \
      -H "Authorization: Bearer $API_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{
      "model_name": "CLF_CYBER_BULLYING_TWEETS",
      "features": [
        "yes exactly the police can murder black people and we can be okay with it because it’s in the past and they’re dead now."
      ],
      "method": "predict"
    }'
    echo ""
    curl -X 'POST' \
      'http://localhost:8080/inference' \
      -H 'accept: application/json' \
      -H "Authorization: Bearer $API_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{
      "model_name": "CLF_CYBER_BULLYING_TWEETS",
      "method": "info"
    }'
    echo ""
    curl -X 'POST' \
      'http://localhost:8080/inference' \
      -H 'accept: application/json' \
      -H "Authorization: Bearer $API_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{
      "model_name": "CLF_CYBER_BULLYING_TWEETS",
      "features": [
        "Today’s society so sensitive it’s sad they joke about everything but they take out the gay jokes before race, rape, and other 'sensitive' jokes",
        "aposto que vou sofrer bullying depois do meu próximo tweet"
      ],
      "targets": [
        "gender",
        "not_cyberbullying"
      ],
      "method": "evaluate"
    }'
    echo ""
    echo ""
    let COUNTER=COUNTER+3
    echo "==> QTY Reqs: $COUNTER"
    echo ""
    echo "    *** Para interromper o teste: Pressione CTRL + c ***"
    echo ""
    sleep $DELAY
done
