# ----------------------------------------------------------------------------------------------------------------------
# Este script executa testes de requisições à Stack de ML (versão Standalone). Os parâmetros de configuração do teste
# estão no script 'optional/test_configs.py'.
#
# No início da tela do teste (ou de cada rodada) são mostradas algumas métricas utilizadas no teste. Segue abaixo  uma
# breve descrição de cada uma delas:
#
# - 'Rodada': Indica qual a rodada que o teste está executando. A cada rodada todos os endpoints são testados, exceto o
#   'get_feedback' que só pode ser executado, para um mesmo modelo, à cada 30 minutos.
# - 'Delay de envio das requisições': Intervalo de tempo em que o script de teste fará cada requisição. Quanto menor
#   for este intervalo, mais recursos computacionais serão exigidos do Worker e/ou da Stack para atender às requisições.
# - 'Tempo decorrido': Tempo decorrido desde o início do teste, em segundos.
# - 'Total de requisições': Total de requisições enviadas para a Stack de ML.
# - 'Taxa de envio': Taxa de envio de requisições expressa em requisições/segundo.
# - 'Total de sobrecargas': Total de vezes que o worker não conseguiu responder à uma requisição num tempo satisfatório.
#   Esse tempo é diretamente relacionado com o parâmtero 'DELAY', configurado no arquivo 'optional/test_configs.py'.
#   Se o delay for muito baixo, uma quantidade maior de requisições são encaminhadas a cada segundo ao worker.
# - 'Aguardando recuperação (pausa: Xs)': Quanto tempo o teste ficou esperando o worker se recuperar das sobrecargas,
#   utilizando uma pausa de X segundos.
# - 'Recuperação/tempo decorrido': Percentual do tempo decorrido do teste que foi gasto aguardando o worker se
#   recuperar das sobrecargas. Se este percentual estiver muito alto, é aconselhável aumentar o tempo de delay ou
#   aumentar quantidade de CPU do worker, esta alteração é feita no arquivo de configuração do docker-compose.
# ----------------------------------------------------------------------------------------------------------------------
import requests
from random import randint
from time import time, sleep
from datetime import datetime
from test_configs import API_TOKEN, API_URL, DELAY, CLEAR_SCREEN, MODEL_NAME, FEATURES, TARGETS
from os import system

# Controla as solicitações de feedback
NEXT_FEEDBACK_TIMESTAMP = -1

# Ajuda a contabilizar a quantidade de requisições efetuadas
TOTAL_REQUESTS = 0

# Quantidade de vezes que o worker sobrecarregou
TOTAL_OVERLOAD = 0

# Tempo que o teste espera para o worker se recurerar de uma sobrecarga
DELAY_PER_OVERLOAD = 10 * DELAY

# Códigos para impressão de mensagens coloridas no terminal
RED = "\033[1;31m"
GREEN = "\033[0;32m"
ORANGE = '\033[33m'
RESET = "\033[0;0m"


def get_job_status(headers, job_id):
    """
    Obtém o status de um job. Se o status estiver como 'Queued', faz 10 tentativas com intervalos de
    'DELAY_PER_OVERLOAD' segundos para tentar obter um status diferente. Se não conseguir, aborta o teste.
        :param headers: Cabeçalho utilizado para obter o status.
        :param job_id: Job ID para consulta do status.
    """
    global TOTAL_OVERLOAD, TOTAL_REQUESTS

    for i in range(10):
        r = requests.post(f"{API_URL}/status", json={"job_id": job_id}, headers=headers)
        resposta = r.json()
        TOTAL_REQUESTS += 1

        if resposta['status'] == 'Queued':
            TOTAL_OVERLOAD += 1
            print(f"\n{ORANGE}* SOBRECARGA #{TOTAL_OVERLOAD}. O job {job_id} ainda está na fila.\n  Tentativa: "
                  f"{i+1}/10.{RESET}", end="", flush=True)

            if i < 9:
                print(f"{ORANGE} Aguardando {DELAY_PER_OVERLOAD} segundo(s) para fazer a próxima tentativa...{RESET}\n")
            else:
                print(f"{ORANGE} Última tentativa!{RESET}\n")

            sleep(DELAY_PER_OVERLOAD)
            continue

        break

    if resposta['status'] == 'Queued':
        print(f"\n{RED}ERROR. O job {job_id} está a mais de {10 * DELAY_PER_OVERLOAD} segundo(s) na fila. "
              f"Provalvelmente os recursos computacionais do(s) 'Worker(s) Pub' e/ou da Stack não serão suficientes "
              f"para atender nessa taxa de requisições por segundo!\n\nConfigure um valor maior que {DELAY} no "
              f"parâmetro 'DELAY', que consta no arquivo de configuração 'optional/test_configs.py'. Reinicie o(s) "
              f"worker(s) 'stack-worker-pub-[1..n]' e rode o teste novamente.{RESET}\n")
        exit(1)

    return resposta


def test_requests(headers):
    """
    Envia várias requisições, conforme parâmetros configurados no arquivo 'optional/test_configs.py', para testar
    a capacidade de resposta da Stack de ML (versão Standalone).
        :param headers: Cabeçalho utilizado nas requisições.
    """
    global NEXT_FEEDBACK_TIMESTAMP, TOTAL_REQUESTS

    print(f"{GREEN}*** Testando o endpoint 'version' ***{RESET}")
    r = requests.get(f"{API_URL}/version", headers={'accept': "application/json"})
    resposta = r.json()
    TOTAL_REQUESTS += 1

    print(f"=> RETORNO: {resposta}\n")

    # Dados para realizar os testes do endpoint 'inference'
    job_id_predict = ""
    inference_requests = [{'model_name': MODEL_NAME, 'features': FEATURES, 'method': "predict"},
                          {'model_name': MODEL_NAME, 'method': "info"},
                          {'model_name': MODEL_NAME, 'features': FEATURES, 'targets': TARGETS, 'method': "evaluate"}]

    print(f"{GREEN}*** Testando o endpoint 'inference' ***{RESET}")

    for ir in inference_requests:
        r = requests.post(f"{API_URL}/inference", json=ir, headers=headers)
        resposta = r.json()
        TOTAL_REQUESTS += 1

        print(f"=> RETORNO ({ir['method']}): {resposta}")

        if resposta['status'] == "Error":
            print(f"\n{RED}ERROR. Consulte o 'RETORNO' para verificar a mensagem de erro!{RESET}\n")
            exit(1)

        sleep(DELAY)
        resposta = get_job_status(headers, resposta['job_id'])
        print(f"=> STATUS DO JOB: {resposta}\n")

        if ir['method'] == "predict":
            job_id_predict = resposta['job_id']

    print(f"{GREEN}*** Testando o endpoint 'feedback' ***{RESET}")

    # Simula o feedback de um label que não participou do treino/retreino do modelo
    fbk_targ = TARGETS if randint(1, 100) < 51 else ["label_novo"]

    print(f"=> INFORMANDO O FEEDBACK {fbk_targ} PARA O JOB: {job_id_predict}")
    r = requests.post(f"{API_URL}/feedback", json={"job_id": job_id_predict, 'feedback': fbk_targ}, headers=headers)
    resposta = r.json()
    TOTAL_REQUESTS += 1

    print(f"=> RETORNO: {resposta}\n")

    if NEXT_FEEDBACK_TIMESTAMP < time():
        print(f"{GREEN}*** Testando o endpoint 'get_feedback' ***{RESET}")
        json_data = {'model_name': MODEL_NAME, 'initial_date': datetime.fromtimestamp(time()).strftime("%d/%m/%Y"),
                     'end_date': datetime.fromtimestamp(time()).strftime("%d/%m/%Y")}

        r = requests.post(f"{API_URL}/get_feedback", json=json_data, headers=headers)
        resposta = r.json()
        TOTAL_REQUESTS += 1

        print(f"=> RETORNO: {resposta}\n")

        if resposta['status'] == "Error":
            if 'next_feedback_timestamp' in resposta:
                NEXT_FEEDBACK_TIMESTAMP = resposta['next_feedback_timestamp']
            else:
                print(f"\n{RED}ERROR. Consulte o 'RETORNO' para verificar a mensagem de erro!{RESET}\n")
                exit(1)

        sleep(DELAY)

        # Verifica de novo porque se for erro por conta do intervalo de feedback o teste não é finalizado
        if resposta['status'] != "Error":
            resposta = get_job_status(headers, resposta['job_id'])
            print(f"=> STATUS DO JOB: {resposta}\n")


if __name__ == "__main__":
    if CLEAR_SCREEN:
        system("clear")

    qty_rodadas = 1
    tempo_decorrido = 0
    inicio = time()
    headers = {'charset': 'utf-8', 'Content-Type': 'application/json', 'Authorization': API_TOKEN}
    data_inicio = datetime.fromtimestamp(inicio).strftime("%d/%m/%Y às %H:%M:%S hs")

    try:
        while True:
            tempo_decorrido = time() - inicio
            print(f"{GREEN}\n\n                                             **************** SIMPLE "
                  f"STRESS TEST - STACK DE ML (STANDALONE) ****************{RESET}\n")
            print(f"=> Modelo: {MODEL_NAME} | Início: {data_inicio}")
            print(f"\n# Rodada..........................: {qty_rodadas}")
            print(f"# Delay de envio das requisições..: {DELAY} segundo(s)")
            print(f"# Tempo decorrido.................: {tempo_decorrido:.2f} segundos = "
                  f"{(tempo_decorrido / 60):.2f} minutos")
            print(f"# Total de requisições............: {TOTAL_REQUESTS}")
            print(f"# Taxa de envio...................: {(TOTAL_REQUESTS / tempo_decorrido):.2f} reqs/seg")
            print(f"# Total de sobrecargas............: {TOTAL_OVERLOAD}")
            tempo_recuperacao = TOTAL_OVERLOAD * DELAY_PER_OVERLOAD
            print(f"# Aguardando recuperação..........: {tempo_recuperacao:.2f} segundo(s) = "
                  f"{(tempo_recuperacao / 60):.2f} minuto(s) | pausa: {DELAY_PER_OVERLOAD} seg")
            print(f"# Recuperação/tempo decorrido.....: {((tempo_recuperacao / tempo_decorrido) * 100):.2f}%\n")
            print(f"                                                          *** Para interromper o teste: Pressione "
                  f"CTRL + c ***")
            print(160 * "-")
            test_requests(headers=headers)
            qty_rodadas += 1
            sleep(DELAY)

            if CLEAR_SCREEN:
                system("clear")
    except KeyboardInterrupt:
        data_fim = datetime.fromtimestamp(time()).strftime("%d/%m/%Y às %H:%M:%S hs")
        print("\n\n********** Teste interrompido pelo usuário **********\n")
        print(f"Modelo..........................: {MODEL_NAME}")
        print(f"Início..........................: {data_inicio}")
        print(f"Fim.............................: {data_fim}")
        print(f"Duração.........................: {((time() - inicio) / 60):.2f} minutos")
        print(f"Rodadas.........................: {qty_rodadas}")
        print(f"Delay de envio das requisições..: {DELAY} segundo(s)")
        print(f"Total de requisições............: {TOTAL_REQUESTS}")
        print(f"Taxa de envio...................: {(TOTAL_REQUESTS / tempo_decorrido):.2f} reqs/seg")
        print(f"Total de sobrecargas............: {TOTAL_OVERLOAD}")
        tempo_recuperacao = TOTAL_OVERLOAD * DELAY_PER_OVERLOAD
        print(f"Aguardando recuperação..........: {(tempo_recuperacao / 60):.2f} minuto(s) | pausa: "
              f"{DELAY_PER_OVERLOAD} seg")
        print(f"Recuperação/tempo decorrido.....: {((tempo_recuperacao / tempo_decorrido) * 100):.2f}%\n")
        exit(0)
    except SystemExit:
        print("\n")  # Ignorado!
    except BaseException as e:
        print(f"\n{RED}ERROR: {e.__class__} - {e}{RESET}\n")
        exit(1)
