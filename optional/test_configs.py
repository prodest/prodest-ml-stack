# --------------------------------------------------------------------------------------------------------------------
# Este script de configuração fornece os parâmetros necessários para o script 'simple_stress_testing.py' para a
# realização de testes simples de stress contra a Stack de ML.
# --------------------------------------------------------------------------------------------------------------------

# Altere conforme a variável 'api_token' que consta no arquivo 'temp_builder/credentials_stack.txt'
API_TOKEN = "COLE_AQUI_O_TOKEN"

# Intervalo entre cada requisição em segundos.
# Pode ser alterado, porém, monitore para verificar se não causará exaustão dos recursos da Stack
DELAY = 0.5

# Define se deve limpar a tela no final de cada rodada do teste. Se não quiser limpar, altere para 'False'
CLEAR_SCREEN = True

# Endereço da API. Só altere se estiver direcionando o teste para outra máquina
API_URL = "http://localhost:8080"

# Caso esteja utilizando o modelo de testes (https://github.com/prodest/modelo-teste), não precisa alterar!
MODEL_NAME = "CLF_CYBER_BULLYING_TWEETS"
FEATURES = ["yes exactly the police can murder black people and we can be okay with it because it’s in the past and "
            "they’re dead now."]
TARGETS = ["ethnicity"]
