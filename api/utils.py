# --------------------------------------------------------------------------------------------------------------------
# Funções, rotinas e variáveis úteis
# --------------------------------------------------------------------------------------------------------------------
import logging
import json
import pika
from pika.exceptions import ChannelClosed
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from hashlib import sha256
from numpy import random
from time import time
from datetime import datetime
from bson import ObjectId
from os import environ as env


def make_log() -> logging.Logger:
    """
    Cria um logger para gerar logs na console.
        :return: Um logger para geração dos logs.
    """
    # Configurações básicas
    logging.basicConfig(level=logging.CRITICAL)
    logger = logging.getLogger("API")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(funcName)s: %(message)s')

    # Configura para gerar logs na console
    logger.propagate = False
    consolehandler = logging.StreamHandler()
    consolehandler.setLevel(logging.INFO)
    consolehandler.setFormatter(formatter)
    logger.addHandler(consolehandler)
    return logger


# Cria o logger
LOGGER = make_log()

LOGGER.info("[*] ------------ Iniciando a API ------------")


def gerar_arquivo_erro():
    """
    Gera um arquivo para indicar que aconteceu um erro. Esse arquivo será utilizado no healthy check do container.
    """
    caminho_arq_erro = "/tmp/error_8EDo2OWK9Sd7A4aN0uni.err"

    try:
        arq = open(caminho_arq_erro, 'w')
    except PermissionError:
        LOGGER.error(f"Não foi possível gerar o arquivo 'error_8EDo2OWK9Sd7A4aN0uni.err', para indicar um erro no "
                     f"container, no caminho '/tmp'. Permissão de escrita negada.")
        exit(1)

    arq.write("Erro. Verifique os logs da aplicação para mais detalhes!\n")
    arq.close()


RABBITMQ_SERVER = env.get('RABBITMQ_SERVER')
if not RABBITMQ_SERVER:
    LOGGER.error("Não foi possível obter a variável de ambiente 'RABBITMQ_SERVER'")
    gerar_arquivo_erro()
    exit(1)

RABBITMQ_PORT = env.get('RABBITMQ_PORT')
if not RABBITMQ_PORT:
    LOGGER.error("Não foi possível obter a variável de ambiente 'RABBITMQ_PORT'")
    gerar_arquivo_erro()
    exit(1)

try:
    RABBITMQ_PORT = int(RABBITMQ_PORT)
except ValueError:
    LOGGER.error("Informe uma porta TCP/IP válida na variável de ambiente 'RABBITMQ_PORT'")
    gerar_arquivo_erro()
    exit(1)

DB_SERVER_NAME = env.get('DB_SERVER_NAME')
if not DB_SERVER_NAME:
    LOGGER.error("Não foi possível obter a variável de ambiente 'DB_SERVER_NAME'")
    gerar_arquivo_erro()
    exit(1)

STK_VERSION = env.get('STACK_VERSION')
if not STK_VERSION:
    LOGGER.error("Não foi possível obter a variável de ambiente 'STACK_VERSION'")
    gerar_arquivo_erro()
    exit(1)

# Obtém o nome da base de dados para autenticação do usuário
DB_AUTH_SOURCE = env.get("DB_AUTH_SOURCE")
if not DB_AUTH_SOURCE:
    LOGGER.error("Não foi possível obter a variável de ambiente 'DB_AUTH_SOURCE'")
    gerar_arquivo_erro()
    exit(1)

# Obtém as credenciais para acesso ao banco de dados
DB_USERNAME = env.get("MONGO_INITDB_ROOT_USERNAME")
if not DB_USERNAME:
    LOGGER.error("Não foi possível obter a variável de ambiente 'MONGO_INITDB_ROOT_USERNAME'")
    gerar_arquivo_erro()
    exit(1)

DB_PASSWORD = env.get("MONGO_INITDB_ROOT_PASSWORD")
if not DB_PASSWORD:
    LOGGER.error("Não foi possível obter a variável de ambiente 'MONGO_INITDB_ROOT_PASSWORD'")
    gerar_arquivo_erro()
    exit(1)

# Obtém as credenciais para interagir com a fila
RABITMQ_USER = env.get("RABBITMQ_DEFAULT_USER")
if not RABITMQ_USER:
    LOGGER.error("Não foi possível obter a variável de ambiente 'RABBITMQ_DEFAULT_USER'")
    gerar_arquivo_erro()
    exit(1)

RABITMQ_PASS = env.get("RABBITMQ_DEFAULT_PASS")
if not RABITMQ_PASS:
    LOGGER.error("Não foi possível obter a variável de ambiente 'RABBITMQ_DEFAULT_PASS'")
    gerar_arquivo_erro()
    exit(1)

# Obtém o token para utilizar nesta instância da API
TOKEN = env.get("API_TOKEN")
if not TOKEN:
    LOGGER.error("Não foi possível obter a variável de ambiente 'API_TOKEN'")
    gerar_arquivo_erro()
    exit(1)

# Obtém a credencial utilizada pelos workers para informarem os seus 'work_id' para validação no cadastro das filas
ADVWORKID_CRED = env.get("ADVWORKID_CREDENTIAL")
if not ADVWORKID_CRED:
    LOGGER.error("Não foi possível obter a variável de ambiente 'ADVWORKID_CREDENTIAL'")
    gerar_arquivo_erro()
    exit(1)

# Obtém o token que será utilizado pelos workers para interagirem com os endpoints internos da API (/retorno, etc.)
TOKEN_WORKERS = env.get("API_TOKEN_WORKERS")
if not TOKEN_WORKERS:
    LOGGER.error("Não foi possível obter a variável de ambiente 'API_TOKEN_WORKERS'")
    gerar_arquivo_erro()
    exit(1)


def connect_db(database_name: str):
    """
    Conecta ao banco de dados e retorna uma instância de client, conectado à base de dados, responsável por fazer
    as interações com o banco.
        :param database_name: Nome da base de dados.
        :return: Instância de client conectado à base de dados.
    """
    client = MongoClient(f"mongodb://%s:%s@{DB_SERVER_NAME}" % (DB_USERNAME, DB_PASSWORD), authSource=DB_AUTH_SOURCE)

    try:
        client.admin.command('ping')
    except ConnectionFailure as e:
        LOGGER.error(f"Servidor de banco de dados indisponível: {e.__class__} - {e}")
        gerar_arquivo_erro()
        exit(1)
    except OperationFailure as e:
        LOGGER.error(f"Falha ao conectar no servidor de banco de dados: {e.__class__} - {e}")
        gerar_arquivo_erro()
        exit(1)

    # Cria alguns índices para a coleção 'col_jobs'. Caso os índices já existam, não faz nada
    try:
        db = client[database_name]
        col = db.col_jobs
        col.create_index([("job_id", 1)], name="idx_jobid")
        col.create_index([("model_name", 1), ("method", 1), ("status", 1)], name="idx_jobs_pred_done")
        col.create_index([("model_name", 1), ("method", 1), ("status", 1), ("has_feedback", 1), ("datetime", 1)],
                         name="idx_getfeedback")
    except BaseException as e:
        LOGGER.error(f"Falha ao tentar criar índices para a coleção 'col_jobs': {e.__class__} - {e}")
        gerar_arquivo_erro()
        exit(1)

    # Define e retorna a conexão com o banco de dados
    return client[database_name]


# Conecta ao banco de dados 'ml_api_db'
CLIENT_BD = connect_db("ml_api_db")


def get_queue_registry_startup():
    """
    Obtém o registro das filas cadastradas, no início da API. Caso não exista, cria um.
         :return: Dicionário contendo o registro das filas.
    """
    col = CLIENT_BD["col_queue_registry"]
    obj_id = ObjectId("000000000000aaaabbbbffff")  # Fixa o _id para facilitar nas buscas e evitar duplicidade de filas

    try:
        result = col.find_one({'_id': obj_id})
    except BaseException as e:
        LOGGER.error(f"Falha ao buscar o registro de filas. Mensagem: {e.__class__} - {e}")
        gerar_arquivo_erro()
        exit(1)

    if not result:
        result = {'_id': obj_id, 'queue_registry': {}}

        try:
            col.insert_one(result)
        except BaseException as e:
            LOGGER.error(f"Não foi possível criar o registro de filas. Mensagem: {e.__class__} - {e}")
            gerar_arquivo_erro()
            exit(1)

    return result['queue_registry']


def enfileirar_job(queue_name, model_name, info_client_host, req_info) -> dict:
    """
    Enfileira um job no servidor de filas.
        :param queue_name: Nome da fila.
        :param model_name: Nome do modelo.
        :param info_client_host: Informações adicionais do cliente que solicitou a execução do job.
        :param req_info: Requisição utilizada para gerar o job que será enfileirado.
        :return: Dicionário com status do enfileiramento e mensagem adicional.
    """
    try:
        # Conecta na fila
        credentials = pika.PlainCredentials(RABITMQ_USER, RABITMQ_PASS)
        parameters = pika.ConnectionParameters(host=RABBITMQ_SERVER, port=RABBITMQ_PORT, credentials=credentials)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        try:
            channel.queue_declare(queue=queue_name, passive=True)
        except ChannelClosed:
            LOGGER.error(f"Origem da requisição: IP={info_client_host}. Erro reportado: Não foi possível enviar o "
                         f"job para a fila '{queue_name}'. A fila está fechada/ausente porque não existem workers "
                         f"escutando esta fila. Modelo: '{model_name}'")
            msg = f"Não foi possível enviar o job para a fila porque não há workers para processá-lo. Verifique " \
                  f"se o modelo '{model_name}' está em produção."
            return {'job_id': "n/a", 'status': "Error", 'response': msg}

        # Envia o job para fila
        payload_encoded = json.dumps(req_info)
        channel.basic_publish(exchange="mlapi_exchange", routing_key=queue_name,
                              body=bytes(payload_encoded.encode("utf-8")))
        connection.close()
    except BaseException as e:
        msg = "Não foi possível enviar o job para a fila. Falha ao tentar conectar no servidor de filas"
        LOGGER.error(f"Origem da requisição: IP={info_client_host}. {msg}. Fila: '{queue_name}'. Modelo: "
                     f"'{model_name}': {e.__class__} - {e}")
        gerar_arquivo_erro()
        return {'job_id': "n/a", 'status': "Error", 'response': msg}

    return {'status': "Done", 'response': ""}


def insert_doc(colecao, doc):
    """
    Insere um documento no banco de dados.
        :param colecao: Coleção onde o documento será inserido.
        :param doc: Documento que será inserido no banco.
        :return: Resultado da inserção.
    """
    try:
        col = CLIENT_BD[colecao]  # Indica a coleção onde os dados serão gravados no banco setado anteriormente
        result = col.insert_one(doc)
    except BaseException as e:
        gerar_arquivo_erro()
        raise e

    return result


def retrieve_doc(colecao, chave, valor):
    """
    Busca e retorna um documento do banco de dados.
        :param colecao: Coleção onde o documento será procurado.
        :param chave: Chave que será utilizada para buscar o documento.
        :param valor: Valor da chave que será utilizado para buscar o documento.
        :return: Documento, caso seja encontrado, None caso contrário.
    """
    try:
        col = CLIENT_BD[colecao]
        result = col.find_one({chave: valor})
    except BaseException as e:
        gerar_arquivo_erro()
        raise e

    return result


def retrieve_docs_feedback(colecao, nome_modelo, initial_date, end_date) -> dict:
    """
    Busca e retorna um conjunto de documentos do banco de dados para realização de feedback de um modelo.
        :param colecao: Coleção onde os documentos serão procurados.
        :param nome_modelo: Nome do modelo.
        :param initial_date: Data inicial (formato dd/mm/yyyy) para realização do feedback.
        :param end_date: Data final (formato dd/mm/yyyy) para realização do feedback.
        :return: Dicionário contendo: status e conjunto de documentos (caso sejam encontrados), ou status e mensagem
                 de erro caso ocorra.
    """
    # A chave 'bloqueia_novo_feedback' será utilizada pela API para ajudar a prevenir o monopólio de recursos
    resultado = {'bloqueia_novo_feedback': False}

    # Valida as datas e converte para timestamp (formato epoch)
    try:
        data_epoch_inicial = datetime.timestamp(datetime.strptime(initial_date, "%d/%m/%Y"))
    except BaseException as e:
        resultado['status'] = "Error"
        resultado['response'] = f"A data inicial está inconsistente. Erro reportado: {e}"
        return resultado

    try:
        data_epoch_final = datetime.timestamp(datetime.strptime(end_date, "%d/%m/%Y"))
        data_epoch_final_mais_1d = data_epoch_final + 86400  # Soma um dia para trazer os jobs do dia inteiro
    except BaseException as e:
        resultado['status'] = "Error"
        resultado['response'] = f"A data final está inconsistente. Erro reportado: {e}"
        return resultado

    if data_epoch_inicial > data_epoch_final:
        resultado['status'] = "Error"
        resultado['response'] = f"A data inicial {initial_date} é maior que a data final {end_date}"
        return resultado

    # Valida o intervalo para saber se está dentro de 90 dias
    intervalo_em_dias = int((data_epoch_final_mais_1d - data_epoch_inicial) / 86400)

    if intervalo_em_dias > 90:
        resultado['status'] = "Error"
        resultado['response'] = f"O intervalo entre as datas {initial_date} e {end_date} é de " \
                                f"{intervalo_em_dias - 1} dias, porém o intervalo máximo permitido para consulta do " \
                                f"feedback é de 90 dias"
        return resultado

    # Forma a query para pesquisar os jobs que tem feedback (vai utilizar o índice 'idx_getfeedback' no mongoDB)
    query_jobs_feedback = {
             'model_name': nome_modelo,
             'method': "predict",
             'status': "Done",
             'has_feedback': True,
             'datetime': {'$gte': data_epoch_inicial, '$lt': data_epoch_final_mais_1d}
    }

    col = CLIENT_BD[colecao]

    # Conta a quantidade de jobs para validar a quantidade máxima, assumindo que cada job terá um único label predito.
    # A quantidade real de labels será validada na API.
    try:
        total_jobs_has_feedback = col.count_documents(filter=query_jobs_feedback, hint="idx_getfeedback")
    except BaseException as e:
        gerar_arquivo_erro()
        raise e

    if total_jobs_has_feedback == 0:
        resultado['status'] = "Error"
        resultado['response'] = f"Não foram encontrados jobs com feedback entre as datas {initial_date} e " \
                                f"{end_date}. Escolha outro intervalo de datas e consulte novamente após 30 minutos"
    elif (total_jobs_has_feedback <= 30000) or (initial_date == end_date):  # Considera o intervalo mínimo de um dia
        # Forma a query para pesquisar os jobs de predict que estão 'Done' (vai utilizar o índice 'idx_jobs_pred_done')
        query_jobs_done = {
            'model_name': nome_modelo,
            'method': "predict",
            'status': "Done",
        }

        try:
            # Auxilia nas estatísticas lá na API
            total_jobs_predict_done = col.count_documents(filter=query_jobs_done, hint="idx_jobs_pred_done")

            resultado['status'] = "Done"
            resultado['total_jobs_predict_done'] = total_jobs_predict_done
            resultado['total_jobs_has_feedback'] = total_jobs_has_feedback

            # Traz na ordem decrescente do campo 'datetime' e limita caso no intervalo de 1 dia existam muitos jobs
            resultado['docs'] = col.find(query_jobs_feedback, hint="idx_getfeedback").sort("datetime", -1).limit(30000)
        except BaseException as e:
            gerar_arquivo_erro()
            raise e
    else:
        resultado['status'] = "Error"
        resultado['response'] = f"Foram encontrados {total_jobs_has_feedback} jobs com feedback entre as datas " \
                                f"{initial_date} e {end_date}. Esta quantidade de jobs ultrapassou a quantidade " \
                                f"máxima (30000) permitida para a consulta de feedback. Escolha um intervalo menor " \
                                f"entre datas e consulte novamente após 30 minutos"

    # Bloqueia, pois se chegou até aqui é porque consultou o banco de dados
    resultado['bloqueia_novo_feedback'] = True

    return resultado


def update_doc(colecao, chave_buscar, valor_buscar, chaves_alterar: dict):
    """
    Atualiza um documento que está no banco.
        :param colecao: Coleção onde o documento será procurado.
        :param chave_buscar: Chave que será utilizada para buscar o documento.
        :param valor_buscar: Valor da chave que será utilizado para buscar o documento.
        :param chaves_alterar: Dicionário contendo as chaves que terão seus valores alterados; e seus
                               respectivos valores.
        :return: Resultado da atualização.
    """
    try:
        col = CLIENT_BD[colecao]
        result = col.update_one({chave_buscar: valor_buscar}, {'$set': chaves_alterar})
    except BaseException as e:
        gerar_arquivo_erro()
        raise e

    return result


def generate_hash(key: str = "key n/a") -> str:
    """
    Gera um hash SHA-256.
        :param key: Chave adicional para gerar o hash.
        :return: Hash SHA-256 gerado.
    """
    # Gera uma chave aleatória para incluir no texto a ser passado para gerar o hash
    lst_key_shuffled = list("eyJzdWIiOiI5NS43OTg0ODk3NTkxMzk5NSIsIm5hbWUiOiJ2YWkgc2Fi")
    random.shuffle(lst_key_shuffled)
    key_shuffled = "".join(lst_key_shuffled)

    h = sha256()
    text = key[:30] + str(time()) + str(random.rand()) + key_shuffled + str(random.rand())
    h.update(text.encode('utf-8'))
    return h.hexdigest()


def validate_request(job_id, job_status, client_host):
    """
    Valida alguns dados da requisição.
        :param job_id: Job ID informado na requisição.
        :param job_status: Status do job informado na requisição.
        :param client_host: Informação do host que fez a requisição.
        :return: Dicionário com o status da validação e a resposta.
    """
    valid_status = ["Done", "Error", "Queued", "Running"]

    if job_status not in valid_status:
        return {'status': "Error", 'response': f"O status informado é inválido. Deve ser (case sensitive): "
                                               f"{valid_status}"}

    # Evita erros na verificação do tamanho
    if type(job_id) is not str:
        job_id = str(job_id)

    tam_job_id = len(job_id)

    # Para evitar gracinhas...
    if tam_job_id > 100:
        LOGGER.error(f"O tamanho do 'job_id' ultrapassou o limite. Tamanho recebido: {tam_job_id}. Origem da "
                     f"requisição: IP={client_host}")
        return {'status': "Error", 'response': f"O tamanho do 'job_id' {job_id} ultrapassou o limite"}

    # Se chegou até aqui, é porque está validado
    return {'status': "Done", 'response': ""}


def save_queue_registry(queue_registry: dict) -> dict:
    """
    Persiste o registro de filas no banco de dados.
        :param queue_registry: Registro de filas.
        :return: True, caso a persistência ocorra com sucesso. False, caso contrário. Também retorna uma mensagem de
                 erro se houver falha.
    """
    obj_id = ObjectId("000000000000aaaabbbbffff")  # Fixa o _id para facilitar nas buscas e evitar duplicidade de filas

    try:
        r = update_doc("col_queue_registry", "_id", obj_id, {'queue_registry': queue_registry})

        if r.modified_count == 0:
            msg = "O registro de filas não foi encontrado"
            LOGGER.error(msg)
            gerar_arquivo_erro()
            return {'status': "Error", 'response': msg}
    except BaseException as e:
        msg = f"Não foi possível salvar o registro de filas: {e.__class__} - {e}"
        LOGGER.error(msg)
        gerar_arquivo_erro()
        return {'status': "Error", 'response': msg}

    return {'status': "Done", 'response': ""}  # Se chegou até aqui, é porque conseguiu salvar


def validate_params(req_info):
    """
    Valida alguns parâmetros passados em uma requisição.
        :param req_info: Requisição recebida do cliente.
        :return: Dicionário com o resultado da validação.
    """
    # Valida se os nomes dos métodos estão corretos e se existem parâmetros específicos para cada um deles.
    # Também valida, se no método evaluate, 'features' e 'targets' tem o mesmo tamanho
    if "method" in req_info:
        metodos = ["predict", "evaluate", "info"]

        if req_info['method'] not in metodos:
            msg = f"O parâmetro 'method' está incorreto. Foi passado '{req_info['method']}', mas deve ser um desses " \
                  f"(case sensitive): {metodos}"
            return {'status': "Error", 'response': msg}

        if req_info['method'] == "predict" or req_info['method'] == "evaluate":
            if "features" not in req_info:
                return {'status': "Error", 'response': f"Faltou informar o parâmetro 'features' na requisição do "
                                                       f"método '{req_info['method']}'"}

        if req_info['method'] == "evaluate":
            if "targets" not in req_info:
                return {'status': "Error", 'response': f"Faltou informar o parâmetro 'targets' na requisição do "
                                                       f"método '{req_info['method']}'"}

            if len(req_info['features']) != len(req_info['targets']):
                msg = f"Os parâmetros 'features' e 'targets' do método '{req_info['method']}' devem ter a mesma " \
                      f"quantidade de elementos"
                return {'status': "Error", 'response': msg}

    # Valida os tipos dos parâmetros e tamanho máximo de alguns
    param_tipos = {'features': list, 'targets': list, 'feedback': list}

    for param, tipo in param_tipos.items():
        if param in req_info:
            tipo_recebido = type(req_info[param])

            if tipo_recebido is not tipo:
                msg = f"O tipo do parâmetro '{param}' está incorreto. Foi recebido '{tipo_recebido.__name__}', mas " \
                      f"deve ser '{tipo.__name__}'"
                return {'status': "Error", 'response': msg}

            if tipo_recebido is list:
                if len(req_info[param]) == 0:
                    return {'status': "Error", 'response': f"Foi passada uma lista vazia no parâmetro '{param}'"}

            # Para evitar monopólio na utilização de recursos dos workers
            if param in ["features", "targets", "feedback"]:
                qtd_itens = len(req_info[param])

                if qtd_itens > 100:
                    msg = f"A quantidade máxima de itens foi ultrapassada. Foram passados {qtd_itens} no parâmetro " \
                          f"'{param}', mas é suportado no máximo 100."
                    return {'status': "Error", 'response': msg}

    # Se chegou até aqui é porque está tudo ok!
    return {'status': "Done", 'response': ""}
