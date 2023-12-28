# --------------------------------------------------------------------------------------------------------------------
# Este script é responsável por atender às requisições, validar algumas premissas e colocá-las nas filas
# para os workers atenderem. Também responde aos pedidos de retorno de status feitos pelos clientes.
#
# >> FLUXO (simplificado!):
#
# - O Cliente envia uma requisição para interagir com um modelo através do endpoint '/inference'.
#
# - No momento em que um worker pega uma requisição que está na fila, ele atualiza o status através do endpoint
#   '/attstatus' para 'running', atende a requisição e informa o resultado através do endpoint '/retorno'.
#
# - A qualquer momento, o cliente que fez a requisição pode consultar o status através do endpoint '/status'. Se
#   o worker já tiver atendido e retornado, o resultado é enviado para o cliente.
# --------------------------------------------------------------------------------------------------------------------
from time import time
from datetime import datetime
from typing import Optional, Union, Annotated
from fastapi import FastAPI, Request, Header, HTTPException, status, Security, Body
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from utils import ObjectId, TOKEN, STK_VERSION, LOGGER, CLIENT_BD, ADVWORKID_CRED, TOKEN_WORKERS, enfileirar_job, \
    generate_hash, insert_doc, validate_request, retrieve_doc, update_doc, save_queue_registry, \
    get_queue_registry_startup, retrieve_docs_feedback, validate_params

# Obtém o registro das filas no início da API
QUEUE_REG = get_queue_registry_startup()

# Parâmetros para fazer o reload do registro das filas para obter as atualizações feitas por outras instâncias da API
QUEUE_REG_RELOAD = {'next_reload': 0.0, 'delay_seconds': 300}

# Ajuda a controlar a periodicidade de feedbacks solicitados globalmente e por modelo.
NEXT_FEEDBACKS_MODELOS = {'next_global_feedback': -1.0}


def reload_queue_registry():
    """
    Lê novamente o registro de filas do banco de dados.
    """
    global QUEUE_REG
    col = CLIENT_BD["col_queue_registry"]
    obj_id = ObjectId("000000000000aaaabbbbffff")  # Fixa o _id para facilitar nas buscas e evitar duplicidade de filas

    try:
        result = col.find_one({"_id": obj_id})

        if result:
            QUEUE_REG = result['queue_registry']
            LOGGER.info("Reload do QUEUE registry -> OK")
    except BaseException as e:
        LOGGER.error(f"Falha ao buscar o registro de filas. Mensagem: {e.__class__} - {e}")


# Informações adicionais para geração de documentação automática da API via Swagger.
# - Referências:
#   https://fastapi.tiangolo.com/tutorial/metadata
#   https://fastapi.tiangolo.com/advanced/path-operation-advanced-configuration/#exclude-from-openapi
#   https://fastapi.tiangolo.com/tutorial/schema-extra-example/#__tabbed_4_2

# Possibilita a autenticação através da interface do Swagger para envio do token de autorização
auth_header = APIKeyHeader(name='Authorization', scheme_name='Bearer token')

# Mostra uma descrição na página de documentação gerada automaticamente pelo Swagger
description = """
API para servir modelos de ML (Machine Learning).

### Endpoints principais

* **inference**: Recebe itens para inferência ou avaliação. Também retorna informações sobre um modelo publicado. 
* **feedback**: Recebe o feedback dos usuários em relação às inferências feitas pelos modelos.
* **get_feedback**: Solicita as informações consolidadas sobre os feedbacks informados pelos usuários.
* **status**: Obtém o status de um job.

### Links úteis
* Repositório da versão standalone para testes da Stack: [Stack de ML Prodest - standalone](https://github.com/prodest/prodest-ml-stack)
* Repositório da lib para publicação de modelos: [mllibprodest - Repo](https://github.com/prodest/mllibprodest) 
* Lib para publicação de modelos no PyPI: [mllibprodest - PyPI](https://pypi.org/project/mllibprodest)
"""

# Define os metadados para cada um dos endpoints de interesse
tags_metadata = [
    {
        "name": "inference",
        "description": "Recebe itens para inferência ou avaliação. Também retorna informações sobre um modelo "
                       "publicado.",
    },
    {
        "name": "feedback",
        "description": "Recebe o feedback dos usuários em relação às inferências feitas pelos modelos.",
    },
    {
        "name": "get_feedback",
        "description": "Solicita as informações consolidadas sobre os feedbacks informados pelos usuários.",
    },
    {
        "name": "status",
        "description": "Obtém o status de um job.",
    },
    {
        "name": "version",
        "description": "Obtém a versão da stack.",
    }
]


# Classes criadas somente para auxiliar na documentação automática do Swagger
class InferenceRequest(BaseModel):
    model_name: str
    features: Optional[list] = None
    targets: Optional[list] = None
    method: str


class StatusRequest(BaseModel):
    job_id: str


class FeedbackRequest(BaseModel):
    job_id: str
    feedback: list


class GetFeedbackRequest(BaseModel):
    model_name: str
    initial_date: str
    end_date: str


def validar_credenciais(token_recebido, is_worker=False):
    """
    Valida as credenciais. Lança uma exceção caso não estejam corretas.
        :param token_recebido: Token recebido através do Header da requisição HTTP.
        :param is_worker: Indica se as credenciais a serem verificadas pertencem a um worker.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Acesso negado! Verifique as credenciais de acesso.",
        headers={"WWW-Authenticate": "Bearer"}
    )
    token_api = TOKEN_WORKERS if is_worker else TOKEN

    if token_recebido:
        # Extrai o token recebido. Obs: O campo de authorization do HEADER vem com o conteúdo "Bearer {token}"
        if token_recebido.split()[-1] != token_api:
            raise credentials_exception
    else:
        raise credentials_exception


# Instancia a API
app = FastAPI(title="API de ML", description=description, openapi_tags=tags_metadata, redoc_url=None)


# Endpoints
@app.get("/", include_in_schema=False)
async def root():
    return {'response': "Hey!, ?oirártnoc oa ocsid o odnivuo átse êcov euq rop"}


# Retorna a versão da stack
@app.get("/version", tags=["version"])
async def version():
    return {"Stack Version": STK_VERSION}


# Endpoint: Realiza as atividades de inferência dos modelos
@app.post("/inference", tags=["inference"])
async def inference(cr: Annotated[
                          InferenceRequest,
                          Body(
                              openapi_examples={
                                  "predict": {
                                      "summary": "Exemplo de predict",
                                      "description": "Solicita a predição de um conjunto de features separadas "
                                                     "por ';'. A quantidade máxima de itens da lista de features é "
                                                     "100.",
                                      "value": {
                                          'model_name': "COLE_AQUI_O_NOME_DO_MODELO",
                                          "features": ["yes exactly the police can murder black people and we can "
                                                       "be okay with it because it’s in the past and they’re dead "
                                                       "now."],
                                          'method': "predict",
                                      },
                                  },
                                  "info": {
                                      "summary": "Exemplo de info",
                                      "description": "Solicita informações sobre um modelo publicado através da API.",
                                      "value": {
                                          'model_name': "COLE_AQUI_O_NOME_DO_MODELO",
                                          'method': "info",
                                      },
                                  },
                                  "evaluate": {
                                      "summary": "Exemplo de avaliação do modelo",
                                      "description": "Solicita uma avaliação do modelo com base em um conjunto de "
                                                     "features e seus targets correspondentes. A quantidade máxima "
                                                     "de itens da lista de features e targets é 100 cada.",
                                      "value": {
                                          "model_name": "COLE_AQUI_O_NOME_DO_MODELO",
                                          "features": ["Today’s society so sensitive it’s sad they joke about "
                                                       "everything but they take out the gay jokes before race, "
                                                       "rape, and other 'sensitive' jokes",
                                                       "aposto que vou sofrer bullying depois do meu próximo tweet"],
                                          "targets": ["gender", "not_cyberbullying"],
                                          "method": "evaluate",
                                      },
                                  },
                              },
                          ),
                      ], info: Request, header_value=Security(auth_header),
                    authorization: Optional[str] = Header(None, include_in_schema=False)):
    validar_credenciais(authorization)
    req_info = await info.json()
    method = req_info['method']

    global QUEUE_REG_RELOAD

    # Obtém as atualizações do registro de filas feitas por outras instâncias da API. Faz em intervalos mínimos de 5 min
    if QUEUE_REG_RELOAD['next_reload'] < time():
        QUEUE_REG_RELOAD['next_reload'] = time() + QUEUE_REG_RELOAD['delay_seconds']
        reload_queue_registry()

    model_name = req_info['model_name']  # Obtém o 'model_name' para verificar qual fila utilizar

    if model_name in QUEUE_REG:
        val = validate_params(req_info)

        if val['status'] == 'Error':
            LOGGER.error(f"Origem da requisição: IP={info.client.host}. Modelo: {model_name}. Erro: {val['response']}")
            return {'job_id': "n/a", 'status': "Error", 'response': val['response']}

        # Obtém o worker_id para utilizar a fila específica do worker
        worker_id = QUEUE_REG[model_name]

        client_key = f"IP_{info.client.host}:{info.client.port}"  # Para ajudar a diversificar o hash
        job_id = generate_hash(client_key)

        # Adiciona o job_id
        req_info['job_id'] = job_id

        # Inclui o token para que o ml worker possa utilizar na atualização de status e retorno
        req_info['token'] = f"Bearer {TOKEN_WORKERS}"

        # Inclui o timestamp para apuração dos tempos de fila e processamento do job
        timestamp = time()
        req_info['datetime'] = timestamp

        resp_enfileirar = enfileirar_job(worker_id, model_name, info.client.host, req_info)

        if resp_enfileirar['status'] != "Done":
            return resp_enfileirar

        try:
            # Coloca o status do job como 'Queued' e persiste
            dados_add = {'job_id': job_id, 'model_name': model_name, 'method': method, 'datetime': timestamp,
                         'status': 'Queued', 'queue_response_time_sec': -1, 'total_response_time_sec': -1,
                         'response': ""}

            # Chaves específicas para o predict
            if method == "predict":
                dados_add['feedback'] = ""
                dados_add['has_feedback'] = False

            insert_doc("col_jobs", dados_add)
        except BaseException as e:
            LOGGER.error(f"Origem da requisição: IP={info.client.host}. Erro reportado: Não foi possível gerar o "
                         f"job. Erro na conexão com o banco de dados: {e.__class__} - {e}")
            return {'job_id': "n/a", 'model_name': model_name, 'method': method, 'status': "Error",
                    'response': "Não foi possível gerar o job. Erro na conexão com o banco de dados"}

        return {'job_id': job_id, 'model_name': model_name, 'method': method, 'status': "Queued"}
    else:
        ret = {'job_id': "n/a", 'model_name': model_name, 'method': method, 'status': "Error",
               'response': "O modelo não foi encontrado!"}
        msg = f"Origem da requisição: IP={info.client.host}. Erro reportado: {ret}"
        LOGGER.error(msg)
        return ret


# Consulta o status do job
@app.post("/status", tags=["status"])
async def get_status(cr: Annotated[
                        StatusRequest,
                        Body(
                            openapi_examples={
                                'status': {
                                    "summary": "Exemplo de solicitação de status",
                                    "description": "Verifica o status de uma solicitação enviada para a API, através "
                                                   "do job_id. Possíveis status: \n\n'Done' = O job foi atendido com "
                                                   "sucesso. Obtenha a resposta utilizando a chave 'response';\n\n"
                                                   "'Error' = Aconteceu algum erro ao tentar atender o job. Obtenha a "
                                                   "mensagem de erro utilizando a chave 'response'; \n\n'Queued' = O "
                                                   "job está aguardando na fila. Se um job estiver há muito tempo na "
                                                   "fila, por exemplo, há mais de 1 minuto, é provável que ele não "
                                                   "seja atendido; \n\n'Running' = O job já foi entregue à algum "
                                                   "worker e está sendo processado. Aqui também, se o job permanecer "
                                                   "por muito tempo nesse estado, pode ser que tenha acontecido algum "
                                                   "erro.",
                                    "value": {
                                        'job_id': "COLE_AQUI_O_JOB_ID",
                                    },
                                },
                            },
                        ),
                        ], info: Request, header_value=Security(auth_header),
                     authorization: Optional[str] = Header(None, include_in_schema=False)):
    validar_credenciais(authorization)
    req_info = await info.json()
    job_id = req_info['job_id']

    # Foi utilizado 'Done' para passar na verificação de status, pois o objetivo é somente validar o job_id
    ret_validate = validate_request(job_id, "Done", info.client.host)

    if ret_validate['status'] == "Error":
        return ret_validate  # Não foi validado, retorna o status e a resposta da rotina de validação

    # Busca o job
    try:
        result = retrieve_doc("col_jobs", "job_id", job_id)

        if result:
            model_name = result['model_name']
            method = result['method']
            status = result['status']
            datetime = result['datetime']
            queue_response_time_sec = result['queue_response_time_sec']
            total_response_time_sec = result['total_response_time_sec']
            response = result['response']

            ret = {'job_id': job_id, 'model_name': model_name, 'method': method, 'status': status,
                   'datetime': datetime, 'queue_response_time_sec': queue_response_time_sec,
                   'total_response_time_sec': total_response_time_sec, 'response': response}

            # Obtenção de chaves específicas dependendo do método
            if method == "predict":
                ret['feedback'] = result['feedback']
                ret['has_feedback'] = result['has_feedback']

            if method == "get_feedback":
                ret['initial_date'] = result['initial_date']
                ret['end_date'] = result['end_date']
                ret['request_source'] = result['request_source']

            return ret
        else:
            msg = f"Não foi possível encontrar o job {job_id}"
            LOGGER.error(f"Origem da requisição: IP={info.client.host}. Erro reportado: {msg}")
            return {'status': "Error", 'response': msg}
    except BaseException as e:
        msg = f"Não foi possível obter o status do job {job_id}. Erro na conexão com o banco de dados"
        LOGGER.error(f"Origem da requisição: IP={info.client.host}. Erro reportado: {msg}: {e.__class__} - {e}")
        return {'status': "Error", 'response': msg}


# Dá feedback em relação às inferências dos modelos
@app.post("/feedback", tags=["feedback"])
async def feedback(cr: Annotated[
                      FeedbackRequest,
                      Body(
                          openapi_examples={
                              "feedback": {
                                  "summary": "Exemplo de feedback",
                                  "description": "Informa o feedback em relação às inferências feitas pelos "
                                                 "modelos. Regras: A lista de feedback deve ter a mesma quantidade de "
                                                 "labels que foi recebida como resposta do job correspondente ao "
                                                 "'job_id' que terá o feedback informado. A quantidade máxima de itens "
                                                 "da lista de feedback é 100.",
                                  "value": {
                                      "job_id": "COLE_AQUI_O_JOB_ID",
                                      "feedback": ["ethnicity"]
                                  },
                              },
                          },
                      ),
                      ], info: Request, header_value=Security(auth_header),
                   authorization: Optional[str] = Header(None, include_in_schema=False)):
    validar_credenciais(authorization)
    req_info = await info.json()
    job_id = req_info['job_id']

    val = validate_params(req_info)

    if val['status'] == 'Error':
        msg = f"Origem da requisição: IP={info.client.host}. Job ID alvo do feedback: {job_id}. Erro reportado: " \
              f"{val['response']}"
        LOGGER.error(msg)
        return {'job_id': "n/a", 'status': "Error", 'response':  val['response']}

    try:
        result = retrieve_doc("col_jobs", "job_id", job_id)

        if result:
            if result['method'] == "predict" and result['status'] == "Done":
                if len(req_info['feedback']) != len(result['response']):
                    msg = f"Não foi possível informar o feedback do job {job_id}. A quantidade de labels informada " \
                          f"no feedback não é a mesma da resposta do job"
                    LOGGER.error(f"Origem da requisição: IP={info.client.host}. Erro reportado: {msg}")
                    return {'status': "Error", 'response': msg}

                # Valida se os tipos dos labels informados no feedback são os mesmos que os das respostas do job
                for i in range(len(result['response'])):
                    tipo_feedback = type(req_info['feedback'][i])
                    tipo_response = type(result['response'][i])

                    if tipo_feedback.__name__ != tipo_response.__name__:
                        msg = f"O tipo do label '{req_info['feedback'][i]}' (posição {i} da lista de feedbacks) é " \
                              f"'{tipo_feedback.__name__}', porém é diferente do que foi informado na resposta " \
                              f"'{result['response'][i]}', que é do tipo '{tipo_response.__name__}'. Verifique se " \
                              f"todos os tipos dos labels informados no feedback são iguais aos da resposta do job " \
                              f"{job_id}"
                        LOGGER.error(f"Origem da requisição: IP={info.client.host}. Erro reportado: {msg}")
                        return {'status': "Error", 'response': msg}

                update_doc("col_jobs", "_id", result['_id'], {'feedback': req_info['feedback'], 'has_feedback': True})
                return {'status': "Done", 'response': f"Feedback informado com sucesso"}
            else:
                msg = f"Não foi possível informar o feedback. O job não é do método 'predict' e/ou o status não é " \
                      f"'Done'. Dados do job {job_id} -> Método: {result['method']}; Status: {result['status']}"
                LOGGER.error(f"Origem da requisição: IP={info.client.host}. Erro reportado: {msg}")
                return {'status': "Error", 'response': f"{msg}"}
        else:
            msg = f"Não foi possível encontrar o job {job_id}"
            LOGGER.error(f"Origem da requisição: IP={info.client.host}. Erro reportado: {msg}")
            return {'status': "Error", 'response': msg}
    except BaseException as e:
        msg = f"Não foi possível informar o feedback para o job {job_id}. Erro na conexão com o banco de dados"
        LOGGER.error(f"Origem da requisição: IP={info.client.host}. Erro reportado: {msg}: {e.__class__} - {e}")
        return {'status': "Error", 'response': msg}


# Consulta o feedback em relação às inferências de um modelo
@app.post("/get_feedback", tags=["get_feedback"])
async def get_feedback(cr: Annotated[
                          GetFeedbackRequest,
                          Body(
                              openapi_examples={
                                  "get_feedback": {
                                      "summary": "Exemplo de solicitação de feedback",
                                      "description": "Solicita o feedback em relação às inferências feitas por um "
                                                     "modelo. Regras: O intervalo máximo entre a data inicial e a "
                                                     "final é de 90 dias. O intervalo entre as solicitações de "
                                                     "feedback de um mesmo modelo deve ser maior que 30 minutos. O "
                                                     "intervalo entre as solicitações de feedback entre modelos "
                                                     "diferentes é de 2 minutos. A quantidade máxima de labels "
                                                     "analisados no feedback é 30000.",
                                      "value": {
                                          'model_name': "COLE_AQUI_O_NOME_DO_MODELO",
                                          "initial_date": "dd/mm/yyyy",
                                          "end_date": "dd/mm/yyyy"
                                      },
                                  },
                              },
                          ),
                          ], info: Request, header_value=Security(auth_header),
                       authorization: Optional[str] = Header(None, include_in_schema=False)):
    validar_credenciais(authorization)
    req_info = await info.json()

    global NEXT_FEEDBACKS_MODELOS
    model_name = req_info['model_name']  # Obtém o 'model_name' para verificar qual fila utilizar

    if model_name in QUEUE_REG:

        # Para evitar monopólio na utilização de recursos da API
        if model_name in NEXT_FEEDBACKS_MODELOS:
            if NEXT_FEEDBACKS_MODELOS[model_name] > time():
                next_feedbk = NEXT_FEEDBACKS_MODELOS[model_name]
                next_feedbk_dt = datetime.fromtimestamp(next_feedbk).strftime("dia %d/%m/%Y a partir das %H:%M:%S hs")
                msg = f"O intervalo entre feedbacks deste modelo não foi respeitado. O próximo feedback poderá ser " \
                      f"solicitado {next_feedbk_dt}"
                LOGGER.error(f"Origem da requisição: IP={info.client.host}. Modelo: {model_name}. Erro: {msg}")
                return {'job_id': "n/a", 'model_name': model_name, 'method': "get_feedback", 'status': "Error",
                        'response': msg, 'next_feedback_timestamp': next_feedbk + 1}

        if NEXT_FEEDBACKS_MODELOS['next_global_feedback'] > time():
            next_global_feedbk = NEXT_FEEDBACKS_MODELOS['next_global_feedback']
            next_global_feedbk_dt = datetime.fromtimestamp(next_global_feedbk).strftime("dia %d/%m/%Y a partir das "
                                                                                        "%H:%M:%S hs")
            msg = f"O intervalo global de 2 minutos entre feedbacks não foi respeitado. O próximo feedback poderá " \
                  f"ser solicitado {next_global_feedbk_dt}"
            LOGGER.error(f"Origem da requisição: IP={info.client.host}. Modelo: {model_name}. Erro: {msg}")
            return {'job_id': "n/a", 'model_name': model_name, 'method': "get_feedback", 'status': "Error",
                    'response': msg, 'next_feedback_timestamp': next_global_feedbk + 1}

        initial_date = req_info['initial_date']
        end_date = req_info['end_date']

        # Obtém o timestamp agora para considerar o tempo de pesquisa no banco e o processamento do retorno
        timestamp = time()

        try:
            ret = retrieve_docs_feedback("col_jobs", model_name, initial_date, end_date)
        except BaseException as e:
            msg = f"Erro ao tentar obter os jobs para realizar o feedback do modelo {model_name}. Falha na conexão " \
                  f"com o banco de dados"
            LOGGER.error(f"Origem da requisição: IP={info.client.host}. Erro reportado: {msg}: {e.__class__} - {e}")
            return {'job_id': "n/a", 'model_name': model_name, 'method': "get_feedback", 'status': "Error",
                    'response': msg}

        # O próximo feedback do modelo só poderá ser solicitado daqui a 30 minutos e o global daqui a 2 minutos
        if ret['bloqueia_novo_feedback']:
            NEXT_FEEDBACKS_MODELOS[model_name] = time() + 1800
            NEXT_FEEDBACKS_MODELOS['next_global_feedback'] = time() + 120

        if ret['status'] != "Done":
            LOGGER.error(f"Origem da requisição: IP={info.client.host}. Modelo: {model_name}. Método: get_feedback. "
                         f"{ret['response']}")
            return {'job_id': "n/a", 'model_name': model_name, 'method': "get_feedback", 'status': ret['status'],
                    'response': ret['response']}

        # Informa o método para o worker utilizar no processamento do job
        req_info['method'] = 'get_feedback'

        # Prepara as listas de labels para enviar para o worker realizar o feedback
        y_pred = []
        y_true = []
        qtd_labels = 0

        # Quantidade de jobs considerados para o feedback. Esta quantidade pode ser diferente da que foi
        # reportada pela função 'retrieve_docs_feedback', por conta de que um job de predict pode ter mais de um label
        # na resposta, assim, pode acontecer de atingir a quantidade máxima de labels com um número menor de jobs
        qtd_jobs_feedback_computados = 0

        for doc in ret['docs']:
            if qtd_labels + len(doc['response']) > 30000:  # Para quando for atingir a quantidade máxima de labels
                break

            y_pred += doc['response']
            y_true += doc['feedback']
            qtd_labels += len(doc['response'])
            qtd_jobs_feedback_computados += 1

        # Fecha o cursor retornado pela função 'retrieve_docs_feedback'
        ret['docs'].close()

        # Acrescenta as informações para o processamento do feedback e algumas outras adicionais
        req_info['y_pred'] = y_pred
        req_info['y_true'] = y_true

        # Coloca as métricas da API em um dicionário para ficarem separadas das métricas retornadas pelos modelos
        metricas_api = {'feedback_labels_types': list(set(y_true))}

        # Trata o caso dos tipos dos labels informados serem diferentes. Caso sejam, fica sem ordenar
        try:
            metricas_api['feedback_labels_types'].sort()
        except TypeError:
            pass

        metricas_api['qty_computed_labels'] = qtd_labels
        metricas_api['total_jobs_predict_done'] = ret['total_jobs_predict_done']
        metricas_api['total_jobs_has_feedback'] = ret['total_jobs_has_feedback']
        metricas_api['total_jobs_computed_feedback'] = qtd_jobs_feedback_computados

        # Informações adicionais
        add_info = f""
        if qtd_jobs_feedback_computados != ret['total_jobs_has_feedback']:
            qtd_jobs_deixados_de_fora = ret['total_jobs_has_feedback'] - qtd_jobs_feedback_computados
            perc_jobs_deixados_de_fora = f"{((qtd_jobs_deixados_de_fora / ret['total_jobs_has_feedback']) * 100):.2f}%"
            add_info += f"Nem todos os jobs que possuem feedback foram processados, pois a quantidade máxima de " \
                        f"labels (30000) por feedback foi alcançada. Foram deixados {qtd_jobs_deixados_de_fora} " \
                        f"jobs de fora do feedback, perfazendo {perc_jobs_deixados_de_fora} dos jobs que tem " \
                        f"feedback. "

        perc_feedbacks = f"{((ret['total_jobs_has_feedback'] / ret['total_jobs_predict_done']) * 100):.2f}%"
        add_info += f"Dos {ret['total_jobs_predict_done']} jobs do método 'predict' que estão com o status 'Done' " \
                    f"(concluídos), {ret['total_jobs_has_feedback']} receberam feedback do usuário, perfazendo " \
                    f"{perc_feedbacks} do total de jobs de 'predict' concluídos"

        metricas_api['additional_info'] = add_info
        req_info['api_metrics'] = metricas_api

        worker_id = QUEUE_REG[model_name]

        client_key = f"IP_{info.client.host}:{info.client.port}"  # Para ajudar a diversificar o hash
        job_id = generate_hash(client_key)

        # Adiciona o job_id
        req_info['job_id'] = job_id

        # Inclui o token para que o ml worker possa utilizar na atualização de status e retorno
        req_info['token'] = f"Bearer {TOKEN_WORKERS}"

        # Ajuda no cálculo do tempo de fila, pois ignora o processamento anterior ao enfileiramento
        req_info['datetime_temp_queue'] = time()

        resp_enfileirar = enfileirar_job(worker_id, model_name, info.client.host, req_info)

        if resp_enfileirar['status'] != "Done":
            return resp_enfileirar

        try:
            # Coloca o status do job como "Queued" e persiste
            dados_add = {'job_id': job_id, 'model_name': model_name, 'method': "get_feedback", 'datetime': timestamp,
                         'status': 'Queued', 'initial_date': initial_date, 'end_date': end_date,
                         'queue_response_time_sec': -1, 'total_response_time_sec': -1, 'response': "",
                         'request_source': info.client.host}
            insert_doc("col_jobs", dados_add)
        except BaseException as e:
            msg = "Não foi possível gerar o job. Erro na conexão com o banco de dados"
            LOGGER.error(f"Origem da requisição: IP={info.client.host}. Erro reportado: {msg}: {e.__class__} - {e}")
            return {'job_id': "n/a", 'model_name': model_name, 'method': "get_feedback", 'status': "Error",
                    'response': msg}

        LOGGER.info(f"A rotina de get_feedback foi executada para o modelo {model_name}, a pedido do cliente "
                    f"{info.client.host}")
        return {'job_id': job_id, 'model_name': model_name, 'method': "get_feedback", 'status': "Queued"}
    else:
        ret = {'job_id': "n/a", 'model_name': model_name, 'method': "get_feedback", 'status': "Error",
               'response': "O modelo não foi encontrado!"}
        msg = f"Origem da requisição: IP={info.client.host}. Erro reportado: {ret}"
        LOGGER.error(msg)
        return ret


# Endpoint interno: O worker-pub atualiza o status do job_id
@app.post("/attstatus", include_in_schema=False)
async def attstatus(info: Request, authorization: Optional[str] = Header(None, include_in_schema=False)):
    validar_credenciais(authorization, is_worker=True)
    req_info = await info.json()
    job_id = req_info['job_id']
    new_status = req_info['newstatus']
    ret_validate = validate_request(job_id, new_status, info.client.host)

    if ret_validate['status'] == "Error":
        return ret_validate  # Não foi validado, retorna o status e a resposta da rotina de validação

    try:
        result = update_doc("col_jobs", "job_id", job_id, {'status': new_status})

        if result.modified_count:
            return {'status': "Done", 'response': ""}  # Não retorna detalhes porque o worker não salva isso no log
        else:
            return {'status': "Error", 'response': f"Não foi possível encontrar o job {job_id}"}
    except BaseException as e:
        msg = f"Não foi possível atualizar o status do job {job_id}. Erro na conexão com o banco de dados"
        LOGGER.error(f"{msg}: {e.__class__} - {e}")
        return {'status': "Error", 'response': msg}


# Endpoint interno: O worker-pub atualiza para "Done" ou "Error" e retorna os resultados do predict
@app.post("/retorno", include_in_schema=False)
async def retorno(info: Request, authorization: Optional[str] = Header(None, include_in_schema=False)):
    validar_credenciais(authorization, is_worker=True)
    req_info = await info.json()
    job_id = req_info['job_id']
    return_status = req_info['status']
    ret_validate = validate_request(job_id, return_status, info.client.host)

    if ret_validate['status'] == "Error":
        return ret_validate  # Não foi validado, retorna o status e a resposta da rotina de validação

    try:
        result = retrieve_doc("col_jobs", "job_id", job_id)

        if result:
            total_response_time_sec = time() - result['datetime']
            campos_atualizar = {'status': return_status, 'queue_response_time_sec': req_info['queue_response_time_sec'],
                                'total_response_time_sec': total_response_time_sec, 'response': req_info['response']}
            update_doc("col_jobs", "_id", result['_id'], campos_atualizar)
            return {'status': "Done", 'response': ""}  # Não retorna detalhes porque o worker não salva isso no log
        else:
            return {'status': "Error", 'response': f"Não foi possível encontrar o job {job_id}"}
    except BaseException as e:
        msg = f"Não foi possível salvar o retorno dos dados e atualizar o status do job {job_id}. Falha na conexão " \
              f"com o banco de dados: {e.__class__} - {e}"
        LOGGER.error(msg)
        return {'status': "Error", 'response': f"{msg}"}


# Endpoint interno: O worker-pub informa o seu 'worker_id' e modelos para validação da criação das filas
@app.post("/advworkid", include_in_schema=False)
async def advworkid(info: Request):
    global QUEUE_REG
    req_info = await info.json()

    if req_info['advworkid_cred'] == ADVWORKID_CRED:
        worker_id = req_info['worker_id']
        models = req_info['models']

        if worker_id:
            LOGGER.info(f"Registrando o worker: {worker_id} ...")

            # Registra os modelos atendidos pelo worker
            for m in models:
                if m not in QUEUE_REG:  # Registra se for novo
                    QUEUE_REG[m] = worker_id
                    resp = save_queue_registry(queue_registry=QUEUE_REG)

                    if resp['status'] == "Done":
                        LOGGER.info(f"Novo modelo cadastrado........................: {m}")
                    else:
                        ret = {'status': "Error", 'response': f"Não foi possível informar o nome do modelo '{m}' e "
                                                              f"worker_id. Retorno da API: {resp['response']}"}
                        LOGGER.error(f"{ret}")
                        return ret
                else:
                    if QUEUE_REG[m] != worker_id:  # Se trocou o worker id, atualiza o worker id responsável pelo modelo
                        old_worker_id = QUEUE_REG[m]
                        QUEUE_REG[m] = worker_id
                        resp = save_queue_registry(queue_registry=QUEUE_REG)

                        if resp['status'] == "Done":
                            LOGGER.info(f"O worker responsável pelo modelo '{m}' foi alterado de {old_worker_id} "
                                        f"para {worker_id}")
                        else:
                            ret = {'status': "Error", 'response': f"Não foi possível informar o nome do modelo '{m}' e "
                                                                  f"worker_id. Retorno da API: {resp['response']}"}
                            LOGGER.error(f"{ret}")
                            return ret

            return {'status': "Done", 'response': f"O 'work_id' {worker_id} e modelo(s) {list(models)} foram "
                                                  f"informados com sucesso!"}
        else:
            ret = {'status': "Error", 'response': "O 'worker_id' está vazio!"}
            LOGGER.error(f"{ret}")
            return ret
    else:
        # Não loga a mensagem de erro para não encher o arquivo de log com requisições sem token de autenticação
        return {'status': "Error", 'response': "A credencial para informar o 'worker_id' e nomes de modelos está "
                                               "incorreta!"}
