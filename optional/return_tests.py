# ----------------------------------------------------------------------------------------------------------------------
# Este script executa testes de requisições à Stack de ML (versão Standalone) para verificar se a validação dos
# parâmetros das requisições está acontecendo com sucesso.
#
# ATENÇÃO: Este teste não cobre mensagens de erro/validação vindas dos Workers, pois são específicas para cada modelo.
# ----------------------------------------------------------------------------------------------------------------------
import json
import requests
from test_configs import API_TOKEN, API_URL, MODEL_NAME, FEATURES, TARGETS
from time import time, sleep
from datetime import datetime

# Códigos para impressão de mensagens coloridas no terminal
RED = "\033[1;31m"
GREEN = "\033[0;32m"
ORANGE = '\033[33m'
RESET = "\033[0;0m"

# Para auxiliar nos testes específicos
JOB_PREDICT_FEEDBACK = ""
JOB_ID_INFO = ""
DATA_GET_FEEDBACK = ""


def carregar_tests():
    """
    Carrega os testes definidos no arquivo 'return_tests_cases.jsonl'.
        :return: Lista contendo as definições dos testes que serão realizados.
    """
    erro_decode = False
    msg_erro_decode = ""
    arq_json = None

    try:
        arq_json = open("return_tests_cases.jsonl", "r")
    except PermissionError:
        print("\nErro ao ler o arquivo 'return_tests_cases.jsonl'. Permissão de leitura negada!\n")
        exit(1)
    except FileNotFoundError:
        print(f"\nErro ao ler o arquivo 'return_tests_cases.jsonl'. Arquivo não encontrado!\n")
        exit(1)

    linhas = []
    testes = []

    try:
        linhas = arq_json.readlines()
    except BaseException as e:
        print(f"Falhou: {e}")
        exit(1)

    # Decodifica os jsons e gera uma lista com as definições dos testes
    for i in range(len(linhas)):
        try:
            testes.append(json.loads(linhas[i].strip('\n')))
        except json.decoder.JSONDecodeError as e:
            erro_decode = True
            msg_erro_decode += f"    JSONL mal formado na linha {i+1}: {e}\n"

    if arq_json:
        arq_json.close()

    if erro_decode:
        print(f"\n{RED}>>> Erro na leitura do arquivo 'return_tests_cases.jsonl':\n\n{msg_erro_decode}{RESET}")
        exit(1)

    return testes


def rodar_testes(headers):
    """
    Roda os testes.
        :param headers: Cabeçalho utilizado para fazer as requisições de teste.
    """
    testes = carregar_tests()
    num_test = 1
    qtd_falhas = 0

    # Testes padrões
    print(f"\n{GREEN}Teste #{num_test}: Testando o endpoint 'version'{RESET}")
    resposta_esperada = {"Stack Version": "rx.y.z (mllibprodest==a.b.c)"}
    r = requests.get(f"{API_URL}/version", headers={'accept': "application/json"})
    resposta = r.json()
    num_test += 1
    print(f"=> Resposta esperada..: {resposta_esperada}")
    print(f"=> Resposta recebida..: {resposta}")
    if "Stack Version" in resposta and resposta['Stack Version'][0] == "r" and resposta['Stack Version'][-1] == ")" \
            and " (mllibprodest==" in resposta['Stack Version']:
        print(f"{GREEN}PASSOU!{RESET}")
    else:
        qtd_falhas += 1
        print(f"{RED}FALHOU!{RESET}")

    print(f"\n{GREEN}Teste #{num_test}: Testando o acesso ao diretório root da API{RESET}")
    resposta_esperada = {"response": "Hey!, ?oirártnoc oa ocsid o odnivuo átse êcov euq rop"}
    r = requests.get(f"{API_URL}/", headers={'accept': "application/json"})
    resposta = r.json()
    num_test += 1
    print(f"=> Resposta esperada..: {resposta_esperada}")
    print(f"=> Resposta recebida..: {resposta}")
    if "response" in resposta and resposta['response'] == "Hey!, ?oirártnoc oa ocsid o odnivuo átse êcov euq rop":
        print(f"{GREEN}PASSOU!{RESET}")
    else:
        qtd_falhas += 1
        print(f"{RED}FALHOU!{RESET}")

    print(f"\n{GREEN}Teste #{num_test}: Requisição sem o token no header{RESET}")
    resposta_esperada = {"detail": "Not authenticated"}
    r = requests.post(f"{API_URL}/status", headers={'accept': "application/json"})
    resposta = r.json()
    num_test += 1
    print(f"=> Resposta esperada..: {resposta_esperada}")
    print(f"=> Resposta recebida..: {resposta}")
    if "detail" in resposta and resposta['detail'] == "Not authenticated":
        print(f"{GREEN}PASSOU!{RESET}")
    else:
        qtd_falhas += 1
        print(f"{RED}FALHOU!{RESET}")

    # Testes específicos
    for teste in testes:
        if 'model_name' in teste['req'] and teste['req']['model_name'] == "MODEL_NAME":
            teste['req']['model_name'] = MODEL_NAME

        if 'model_name' in teste['resp'] and teste['resp']['model_name'] == "MODEL_NAME":
            teste['resp']['model_name'] = MODEL_NAME

        if 'detail' in teste['resp'] and 'input' in teste['resp']['detail'][0]:
            if type(teste['resp']['detail'][0]['input']) is dict:
                if 'model_name' in teste['resp']['detail'][0]['input'] and \
                        teste['resp']['detail'][0]['input']['model_name'] == "MODEL_NAME":
                    teste['resp']['detail'][0]['input']['model_name'] = MODEL_NAME

        if 'features' in teste['req'] and teste['req']['features'] == "FEATURES":
            teste['req']['features'] = FEATURES

        if 'targets' in teste['req'] and teste['req']['targets'] == "TARGETS":
            teste['req']['targets'] = TARGETS

        if 'job_id' in teste['req'] and teste['req']['job_id'] == "JOB_PREDICT_FEEDBACK":
            teste['req']['job_id'] = JOB_PREDICT_FEEDBACK

        if 'detail' in teste['resp'] and 'input' in teste['resp']['detail'][0]:
            if type(teste['resp']['detail'][0]['input']) is dict:
                if 'job_id' in teste['resp']['detail'][0]['input'] and \
                        teste['resp']['detail'][0]['input']['job_id'] == "JOB_PREDICT_FEEDBACK":
                    teste['resp']['detail'][0]['input']['job_id'] = JOB_PREDICT_FEEDBACK

        if 'job_id' in teste['req'] and teste['req']['job_id'] == "JOB_ID_INFO":
            teste['req']['job_id'] = JOB_ID_INFO
            msg_split = teste['resp']['response'].split("#")
            teste['resp']['response'] = f"{msg_split[0]}{JOB_ID_INFO}{msg_split[1]}"

        if 'initial_date' in teste['req'] and teste['req']['initial_date'] == "DATA_GET_FEEDBACK":
            teste['req']['initial_date'] = DATA_GET_FEEDBACK

        if 'detail' in teste['resp'] and 'input' in teste['resp']['detail'][0]:
            if type(teste['resp']['detail'][0]['input']) is dict:
                if 'initial_date' in teste['resp']['detail'][0]['input'] and \
                        teste['resp']['detail'][0]['input']['initial_date'] == "DATA_GET_FEEDBACK":
                    teste['resp']['detail'][0]['input']['initial_date'] = DATA_GET_FEEDBACK

        if 'end_date' in teste['req'] and teste['req']['end_date'] == "DATA_GET_FEEDBACK":
            teste['req']['end_date'] = DATA_GET_FEEDBACK

        if 'detail' in teste['resp'] and 'input' in teste['resp']['detail'][0]:
            if type(teste['resp']['detail'][0]['input']) is dict:
                if 'end_date' in teste['resp']['detail'][0]['input'] and \
                        teste['resp']['detail'][0]['input']['end_date'] == "DATA_GET_FEEDBACK":
                    teste['resp']['detail'][0]['input']['end_date'] = DATA_GET_FEEDBACK

        print(f"\n{GREEN}Teste #{num_test}: {teste['desc']}{RESET}")
        r = requests.post(f"{API_URL}/{teste['endpoint']}", json=teste['req'], headers=headers)
        resposta = r.json()
        num_test += 1
        print(f"=> Requisição ........: {teste['req']}")
        print(f"=> Resposta esperada..: {teste['resp']}")
        print(f"=> Resposta recebida..: {resposta}")
        if teste['resp'] == resposta:
            print(f"{GREEN}PASSOU!{RESET}")
        else:
            qtd_falhas += 1
            print(f"{RED}FALHOU!{RESET}")

    if qtd_falhas == 0:
        print(f"\n\n{GREEN}    **** PASSOU EM TODOS OS {num_test-1} TESTES!{RESET}")
        cor_texto = GREEN
    elif qtd_falhas == num_test:
        print(f"\n\n{RED}    **** FALHOU EM TODOS OS TESTES!{RESET}")
        cor_texto = RED
    else:
        print(f"\n\n{RED}    **** FALHOU EM {qtd_falhas}/{num_test-1} ({(qtd_falhas / (num_test-1)) * 100:.2f}%) DOS "
              f"TESTES! {RESET}")
        cor_texto = RED

    print(f"{cor_texto}    **** Verifique as mensagens acima para mais detalhes.{RESET}\n\n")


def preparar_testes(headers):
    """
    Obtém alguns dados para a execução dos testes específicos.
        :param headers: Cabeçalho utilizado para fazer as requisições.
    """
    global JOB_PREDICT_FEEDBACK, JOB_ID_INFO, DATA_GET_FEEDBACK
    falhou = False

    # Obtém os job_ids para realizar os testes
    print(f"\n{GREEN}=> Obtendo o 'job_id' de 'predict' para auxiliar nos testes{RESET}")
    ir = {'model_name': MODEL_NAME, 'features': FEATURES, 'method': "predict"}
    r = requests.post(f"{API_URL}/inference", json=ir, headers=headers)
    resposta = r.json()
    if resposta['status'] != "Error":
        JOB_PREDICT_FEEDBACK = resposta['job_id']
    else:
        falhou = True

    print(f"RETORNO: {resposta}")

    print(F"\n{GREEN}=> Obtendo o 'job_id' de 'info' para auxiliar nos testes{RESET}")
    ir = {'model_name': MODEL_NAME, 'method': "info"}
    r = requests.post(f"{API_URL}/inference", json=ir, headers=headers)
    resposta = r.json()

    if resposta['status'] != "Error":
        JOB_ID_INFO = resposta['job_id']
    else:
        falhou = True

    print(f"RETORNO: {resposta}")

    if falhou:
        print(f"\n\n{RED}Falha na preparação dos testes. Verifique o(s) retorno(s) acima para mais detalhes!{RESET}")
        exit(1)

    # Obtém a data para realização dos testes
    DATA_GET_FEEDBACK = datetime.fromtimestamp(time()).strftime("%d/%m/%Y")

    print("\nDando um tempo para os jobs serem processados...", end="", flush=True)
    sleep(2)
    print("\n")


if __name__ == "__main__":
    headers = {'charset': 'utf-8', 'Content-Type': 'application/json', 'Authorization': API_TOKEN}
    print(f"{GREEN}\n\n                                             **************** RETURN TESTS ****************"
          f"{RESET}\n")

    try:
        preparar_testes(headers)
        rodar_testes(headers)
    except SystemExit:
        print("\n")  # Ignorado!
    except BaseException as e:
        print(f"\n{RED}ERROR: {e.__class__} - {e}{RESET}\n")
        exit(1)
