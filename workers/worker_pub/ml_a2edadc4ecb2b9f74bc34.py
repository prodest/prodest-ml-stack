# --------------------------------------------------------------------------------------------------------------------
# Este script é responsável por pegar/receber os jobs da fila, validar algumas premissas e atender aos jobs
# utilizando os modelos de sua responsabilidade.
#
# >> FLUXO (simplificado!):
#
# - O worker pega/recebe um job que está na fila.
# - Atualiza o status através do endpoint '/attstatus' para 'Running'.
# - Atende ao job e informa o resultado através do endpoint '/retorno'.
#
# ATENÇÃO: Várias partes deste código foram retiradas/inspiradas em um exemplo do repositório oficial da lib pika:
# https://github.com/pika/pika/blob/main/examples/basic_consumer_threaded.py
# --------------------------------------------------------------------------------------------------------------------
import pika
import json
import requests
import threading
import functools
import weakref
from json import dumps
from time import time
from mllibprodest.utils import make_log
from mllibprodest.initiators.model_initiator import InitModels as Im
from os import environ as env
from pika.exchange_type import ExchangeType


# Cria (ou abre) o arquivo de logs para o worker e retorna o logger para geração dos logs
LOGGER = make_log("worker_pub.log")

# Obtém as credenciais para informar o nome da fila para API
ADVWORKID_CRED = env.get("ADVWORKID_CREDENTIAL")
if not ADVWORKID_CRED:
    LOGGER.error("Não foi possível obter a variável de ambiente 'ADVWORKID_CREDENTIAL'")
    exit(1)

WORKER_ID = env.get("WORKER_ID_001")
if not WORKER_ID:
    LOGGER.error("Não foi possível obter a variável de ambiente 'WORKER_ID_001'")
    exit(1)

API_URL = env.get('API_URL')
if not API_URL:
    LOGGER.error("Não foi possível obter a variável de ambiente 'API_URL'")
    exit(1)

RABBITMQ_SERVER = env.get('RABBITMQ_SERVER')
if not RABBITMQ_SERVER:
    LOGGER.error("Não foi possível obter a variável de ambiente 'RABBITMQ_SERVER'")
    exit(1)

RABBITMQ_PORT = env.get('RABBITMQ_PORT')
if not RABBITMQ_PORT:
    LOGGER.error("Não foi possível obter a variável de ambiente 'RABBITMQ_PORT'")
    exit(1)

try:
    RABBITMQ_PORT = int(RABBITMQ_PORT)
except ValueError:
    LOGGER.error("Informe uma porta TCP/IP válida na variável de ambiente 'RABBITMQ_PORT'")
    exit(1)

# Obtém as credenciais para interagir com a fila
RABITMQ_USER = env.get("RABBITMQ_DEFAULT_USER")
if not RABITMQ_USER:
    LOGGER.error("Não foi possível obter a variável de ambiente 'RABBITMQ_DEFAULT_USER'")
    exit(1)

RABITMQ_PASS = env.get("RABBITMQ_DEFAULT_PASS")
if not RABITMQ_PASS:
    LOGGER.error("Não foi possível obter a variável de ambiente 'RABBITMQ_DEFAULT_PASS'")
    exit(1)

LOGGER.info("[*] Instanciando o(s) modelo(s) de ML...")
try:
    MODELOS = Im.init_models()
except BaseException as e:
    LOGGER.error(f"Não foi possível instanciar o(s) modelo(s). Mensagem do 'init_models': {e.__class__} - {e}",
                 exc_info=True)
    raise e


class WeakObj:
    """
    Encapsula objetos para possibilitar a criação de referências fracas (via weakref).
    """
    def __init__(self, obj):
        self.__obj = obj

    def get_obj(self):
        """
        Retorna o objeto encapsulado.
        """
        return self.__obj


def ack_message(ch, delivery_tag):
    """
    Reconhece (ack) uma mensagem recebida pela função 'do_work'.
        :param ch: Canal pika.
        :param delivery_tag: Tag referente à mensagem que será reconhecida.
    """
    # Note that `ch` must be the same pika channel instance via which
    # the message being ACKed was retrieved (AMQP protocol constraint).
    if ch.is_open:
        ch.basic_ack(delivery_tag)


def do_work(ch, delivery_tag, body):
    """
    Processa os jobs recebidos da fila.
        :param ch: Canal pika.
        :param delivery_tag: Tag referente à mensagem recebida.
        :param body: Corpo da mensagem recebida.
    """
    # OBS.: utilizando o weakref para deixar a função mais robusta, pois a depender do modelo, podem vir dados pesados.
    # Portanto, tenta-se garantir com o weakref que não haja objetos grandes ocupando a memória desnecessariamente
    json_data_obj = WeakObj(json.loads(body))
    json_data_wref = weakref.ref(json_data_obj)
    json_data = json_data_wref()

    # Apura o tempo que o job ficou em fila aguardando pelo worker
    if json_data.get_obj()['method'] != "get_feedback":
        queue_response_time_sec = time() - json_data.get_obj()['datetime']
    else:
        queue_response_time_sec = time() - json_data.get_obj()['datetime_temp_queue']

    headers = {'charset': 'utf-8', 'Content-Type': 'application/json', 'Authorization': json_data.get_obj()['token']}
    valores_ok = False  # Verifica se os valores necessários foram encontrados
    post_status_ok = False  # Verifica se o worker conseguiu atualizar o status do job

    # URLs para interação com os endpoints 'internos'
    url_status = f"{API_URL}/attstatus"
    url_retorno = f"{API_URL}/retorno"

    # Obtém os valores necessários para atender à requisição
    job_id = "n/a"
    model_name = ""
    metodo = ""

    try:
        job_id = json_data.get_obj()['job_id']
        model_name = json_data.get_obj()['model_name']
        metodo = json_data.get_obj()['method']

        if metodo not in ["get_feedback", "info"]:
            features_obj = WeakObj(json_data.get_obj()['features'])
            features_wref = weakref.ref(features_obj)
            features = features_wref()

        if metodo == "evaluate":
            targets_obj = WeakObj(json_data.get_obj()['targets'])
            targets_wref = weakref.ref(targets_obj)
            targets = targets_wref()

        if metodo == "get_feedback":
            y_pred_obj = WeakObj(json_data.get_obj()['y_pred'])
            y_pred_wref = weakref.ref(y_pred_obj)
            y_pred = y_pred_wref()

            y_true_obj = WeakObj(json_data.get_obj()['y_true'])
            y_true_wref = weakref.ref(y_true_obj)
            y_true = y_true_wref()

        valores_ok = True
    except KeyError as e:
        retorno_obj = WeakObj({'job_id': job_id, 'status': "Error",
                               'response': f"Faltou informar esta chave na requisição: {e}",
                               'queue_response_time_sec': queue_response_time_sec})
        retorno_wref = weakref.ref(retorno_obj)
        retorno = retorno_wref()
        LOGGER.error(f"{retorno.get_obj()}")

    if valores_ok:
        # Fazendo call para API para atualizar o status para 'Running'
        try:
            r = requests.post(url_status, json={'job_id': job_id, 'newstatus': 'Running'}, headers=headers)
            resposta = r.json()

            if resposta['status'] == "Done":
                post_status_ok = True
            else:
                LOGGER.error(f"{resposta['response']}")
                retorno_obj = WeakObj({'job_id': job_id, 'status': "Error", 'response': resposta['response'],
                                       'queue_response_time_sec': queue_response_time_sec})
                retorno_wref = weakref.ref(retorno_obj)
                retorno = retorno_wref()
        except BaseException as e:
            # Evita expor exceção do worker para o cliente, mas guarda no log
            dados_erro_obj = WeakObj({'job_id': job_id, 'status': "Error", 'response': f"{e.__class__} - {e}"})
            dados_erro_wref = weakref.ref(dados_erro_obj)
            dados_erro = dados_erro_wref()
            LOGGER.error(f"Não foi possível atualizar o status do job: {dados_erro.get_obj()}")
            retorno_obj = WeakObj({'job_id': job_id, 'status': "Error", 'response': "Não foi possível atualizar o "
                                                                                    "status do job.",
                                   'queue_response_time_sec': queue_response_time_sec})
            retorno_wref = weakref.ref(retorno_obj)
            retorno = retorno_wref()

        if post_status_ok:
            # Se foi passado o nome do modelo corretamente, escolhe o modelo para atender à requisição
            if model_name in MODELOS:
                tipo_retorno_ok = True
                modelo = MODELOS[model_name]

                # Previne que exceções vindas dos modelos derrubem o worker; e manda a mensagem de erro para o cliente
                try:
                    if metodo == "predict":
                        retorno_modelo_obj = WeakObj(modelo.predict(dataset=features.get_obj()))
                        del features
                        retorno_modelo_wref = weakref.ref(retorno_modelo_obj)
                        retorno_modelo = retorno_modelo_wref()
                        tipo_retorno = type(retorno_modelo.get_obj())

                        if tipo_retorno is not list and tipo_retorno is not str:
                            tipo_retorno_ok = False
                            del retorno_modelo
                            retorno_modelo = f"O tipo de retorno do método 'predict' está incorreto. Deve ser " \
                                             f"'list' ou 'str', mas retornou '{tipo_retorno.__name__}'"
                    elif metodo == "evaluate":
                        retorno_modelo_obj = WeakObj(modelo.evaluate(data_features=features.get_obj(),
                                                                     data_targets=targets.get_obj()))
                        del features, targets
                        retorno_modelo_wref = weakref.ref(retorno_modelo_obj)
                        retorno_modelo = retorno_modelo_wref()
                        tipo_retorno = type(retorno_modelo.get_obj())

                        if tipo_retorno is not dict and tipo_retorno is not str:
                            tipo_retorno_ok = False
                            del retorno_modelo
                            retorno_modelo = f"O tipo de retorno do método 'evaluate' está incorreto. Deve ser " \
                                             f"'dict' ou 'str', mas retornou '{tipo_retorno.__name__}'"
                    elif metodo == "get_feedback":
                        # Esse retorno é temporário porque depois ele será colocado como valor da chave 'model_metrics'
                        retorno_modelo_temp_obj = WeakObj(modelo.get_feedback(y_pred=y_pred.get_obj(),
                                                                              y_true=y_true.get_obj()))
                        del y_pred, y_true
                        retorno_modelo_temp_wref = weakref.ref(retorno_modelo_temp_obj)
                        retorno_modelo_temp = retorno_modelo_temp_wref()
                        tipo_retorno = type(retorno_modelo_temp.get_obj())

                        if tipo_retorno is dict or tipo_retorno is str:
                            # Cria um dicionário para separar as métricas vindas do modelo das vindas da API ou retorna
                            # o erro reportado pelo método 'get_feedback'
                            if tipo_retorno is dict:
                                retorno_modelo_obj = WeakObj({'model_metrics': retorno_modelo_temp.get_obj()})
                            else:
                                retorno_modelo_obj = WeakObj(retorno_modelo_temp.get_obj())

                            retorno_modelo_wref = weakref.ref(retorno_modelo_obj)
                            retorno_modelo = retorno_modelo_wref()
                        else:
                            tipo_retorno_ok = False
                            retorno_modelo = f"O tipo de retorno do método 'get_feedback' está incorreto. Deve ser " \
                                             f"'dict' ou 'str', mas retornou '{tipo_retorno.__name__}'"
                        del retorno_modelo_temp
                    elif metodo == "info":
                        retorno_modelo_obj = WeakObj(modelo.get_model_info())
                        retorno_modelo_wref = weakref.ref(retorno_modelo_obj)
                        retorno_modelo = retorno_modelo_wref()
                        tipo_retorno = type(retorno_modelo.get_obj())

                        if tipo_retorno is not dict and tipo_retorno is not str:
                            tipo_retorno_ok = False
                            del retorno_modelo
                            retorno_modelo = f"O tipo de retorno do método 'get_model_info' está incorreto. Deve ser " \
                                             f"'dict' ou 'str', mas retornou '{tipo_retorno.__name__}'"

                    # Prepara o retorno
                    retorno_obj = WeakObj({'job_id': job_id, 'queue_response_time_sec': queue_response_time_sec})
                    retorno_wref = weakref.ref(retorno_obj)
                    retorno = retorno_wref()

                    # Obtém a versão do modelo para incluir no retorno
                    model_version_obj = WeakObj(modelo.get_model_version())
                    model_version_wref = weakref.ref(model_version_obj)
                    model_version = model_version_wref()
                    tipo_retorno_model_version = type(model_version.get_obj())

                    if tipo_retorno_model_version is not str:
                        tipo_retorno_ok = False
                        del retorno_modelo, model_version
                        retorno.get_obj()['model_version'] = ""  # Para não dar erro de chave não encontrada na API
                        retorno_modelo = f"O tipo de retorno do método 'get_model_version' está incorreto. Deve ser " \
                                         f"'str', mas retornou '{tipo_retorno_model_version.__name__}'"

                    if tipo_retorno_ok:
                        # Se o tipo do retorno do modelo for 'str' significa de aconteceu algum erro
                        if tipo_retorno is not str:
                            retorno.get_obj()['status'] = "Done"
                            retorno.get_obj()['model_version'] = model_version.get_obj()

                            # Inclui as informações adicionais sobre o feedback vindas da API
                            if metodo == "get_feedback":
                                retorno_modelo.get_obj()['api_metrics'] = json_data.get_obj()['api_metrics']
                        else:
                            retorno.get_obj()['status'] = "Error"  # Erro reportado pelo modelo

                        retorno.get_obj()['response'] = retorno_modelo.get_obj()
                    else:
                        retorno.get_obj()['status'] = "Error"  # Erro reportado pela API. Motivo: tipo de retorno errado
                        retorno.get_obj()['response'] = retorno_modelo

                    del retorno_modelo
                except BaseException as e:
                    # Expondo exceção que está vindo do modelo para o cliente, para facilitar o diagnóstico da falha
                    msg = f"O modelo '{model_name}' reportou o seguinte erro ao tentar processar o job: " \
                          f"{e.__class__} - {e}"
                    retorno_obj = WeakObj({'job_id': job_id, 'status': "Error",
                                           'queue_response_time_sec': queue_response_time_sec, 'response': msg})
                    retorno_wref = weakref.ref(retorno_obj)
                    retorno = retorno_wref()
                    LOGGER.error(f"{retorno.get_obj()}", exc_info=True)
            else:
                retorno_obj = WeakObj({'job_id': job_id, 'status': "Error", 'response': f"O modelo '{model_name}' não "
                                                                                        f"foi encontrado!",
                                       'queue_response_time_sec': queue_response_time_sec})
                retorno_wref = weakref.ref(retorno_obj)
                retorno = retorno_wref()
                LOGGER.error(f"{retorno.get_obj()}")

    try:
        r = requests.post(url_retorno, json=retorno.get_obj(), headers=headers)
        resposta = r.json()

        if resposta['status'] != "Done":
            LOGGER.error(f"{resposta}")
    except BaseException as e:
        LOGGER.error(f"Não foi possível retornar a resposta para a API ao processar o job {job_id}: "
                     f"{e.__class__} - {e}", exc_info=True)
        if e.__class__ is TypeError:
            LOGGER.info(f"----> DUMPS do JSON do retorno para verificar a(s) chave(s) com problema (observe os "
                        f"caracteres de escape e aspas): \n{repr(dumps(retorno.get_obj(), default=str))}")

    del json_data, retorno

    # Solicita o reconhecimento (ack) da mensagem recebida
    cb = functools.partial(ack_message, ch, delivery_tag)
    ch.connection.add_callback_threadsafe(cb)


def on_message(ch, method_frame, _header_frame, body, args):
    """
    Função principal de callback.
    """
    thrds = args
    delivery_tag = method_frame.delivery_tag
    t = threading.Thread(target=do_work, args=(ch, delivery_tag, body))
    t.start()
    thrds.append(t)


if __name__ == "__main__":
    LOGGER.info("[*] Iniciando o processamento da engine de ML...")

    # Guarda as versões de cada modelo para auxiliar na realização de health check do container
    models_ver = {}

    for nome_modelo, modelo in MODELOS.items():
        models_ver[nome_modelo] = modelo.get_model_version()

    # Obtém um modelo qualquer para utilizar o método 'convert_artifact_to_pickle' para auxiliar na persistência
    modelo_aux = MODELOS[list(MODELOS.keys())[0]]

    modelo_aux.convert_artifact_to_pickle(model_name="", artifact=models_ver, file_name="runid_models.pkl", path="/tmp")
    LOGGER.info("Arquivo de versões dos modelos, para realizar o health check do Worker, gerado com sucesso no caminho "
                "'/tmp/runid_models.pkl'")

    del models_ver, modelo_aux

    # Montando a requisição para informar o 'WORKER_ID' para a API
    url_advworkid = f"{API_URL}/advworkid"
    headers = {'charset': 'utf-8', 'Content-Type': 'application/json'}
    dados = {'advworkid_cred': ADVWORKID_CRED, 'worker_id': WORKER_ID, 'models': list(MODELOS.keys())}

    LOGGER.info("[*] Informando o 'WORKER_ID' para a API...")
    resposta = None

    try:
        r = requests.post(url_advworkid, json=dados, headers=headers)
        resposta = r.json()
    except BaseException as e:
        LOGGER.error(f"{e.__class__} - {e}")
        exit(1)

    if resposta:
        if resposta['status'] == "Done":
            LOGGER.info(f"{resposta}")

            try:
                credentials = pika.PlainCredentials(RABITMQ_USER, RABITMQ_PASS)
                parameters = pika.ConnectionParameters(host=RABBITMQ_SERVER, port=RABBITMQ_PORT, heartbeat=10,
                                                       credentials=credentials)
                connection = pika.BlockingConnection(parameters)
                channel = connection.channel()
                channel.exchange_declare(
                    exchange="mlapi_exchange",
                    exchange_type=ExchangeType.direct,
                    passive=False,
                    durable=True,
                    auto_delete=False)
                channel.queue_declare(queue=WORKER_ID, auto_delete=True)
                channel.queue_bind(queue=WORKER_ID, exchange="mlapi_exchange", routing_key=WORKER_ID)

                # Note: prefetch is set to 1 here as an example only and to keep the number of threads created
                # to a reasonable amount. In production, you will want to test with different prefetch values
                # to find which one provides the best performance and usability for your solution
                channel.basic_qos(prefetch_count=1)

                threads = []
                on_message_callback = functools.partial(on_message, args=threads)
                channel.basic_consume(on_message_callback=on_message_callback, queue=WORKER_ID)
                LOGGER.info(f"[*] Aguardando por mensagens. FILA={WORKER_ID} - Para sair pressione CTRL+c")

                try:
                    channel.start_consuming()
                except KeyboardInterrupt:
                    channel.stop_consuming()

                # Wait for all to complete
                for thread in threads:
                    thread.join()

                connection.close()
            except BaseException as e:
                LOGGER.error(f"Erro na conexão/escuta da fila: {e.__class__} - {e}")
                exit(1)
        else:
            LOGGER.error(f"{resposta}")
            exit(1)
