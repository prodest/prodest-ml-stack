# -------------------------------------------------------------------------------------------------------------------
# Script responsável por fazer um health check para verificar se o Worker está com os modelos atualizados. Caso
# exista algum modelo desatualizado, coloca o container no estado 'unhealthy'.
# -------------------------------------------------------------------------------------------------------------------
import warnings
import pickle
from mllibprodest.utils import make_log
from mllibprodest.providers_types.utils import get_models_versions_providers
from pathlib import Path

# Cria (ou abre) o arquivo de logs para o script e retorna o logger para geração dos logs
LOGGER = make_log("worker_pub_health_check.log")


def convert_artifact_to_object(file_name: str, path: str):
    """
    Converte um artefato que está no formato pickle para o objeto de origem.
        :param file_name: Nome do arquivo que será lido e convertido.
        :param path: Caminho onde o arquivo a ser convertido se encontra.
        :return: Artefato convertido.
    """
    caminho_artefato = str(Path(path) / file_name)

    try:
        arq = open(caminho_artefato, 'rb')
    except FileNotFoundError:
        LOGGER.error(f"Não foi possível converter o artefato '{file_name}'. O caminho '{caminho_artefato}' não foi "
                     f"encontrado.")
        exit(1)
    except PermissionError:
        LOGGER.error(f"Não foi possível converter o artefato '{file_name}' usando o caminho '{caminho_artefato}'. "
                     f"Permissão de leitura negada.")
        exit(1)

    try:
        objeto = pickle.load(arq)
    except pickle.UnpicklingError as e:
        LOGGER.error(f"Não foi possível converter o artefato '{file_name}' com o Pickle (mensagem Pickle: {e}).")
        exit(1)

    arq.close()

    return objeto


LOGGER.info("[*] Obtendo as versões dos modelos de ML para realizar o health check do Worker...")
try:
    # Evita os warnings que estão atrapalhando a saida do script
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        MODELOS_VERSOES = get_models_versions_providers()
except BaseException as e:
    LOGGER.error(f"Não foi possível obter as versões dos modelos. Mensagem do 'get_models_versions_providers': "
                 f"{e.__class__} - {e}",
                 exc_info=True)
    exit(1)


def verificar_dados_modelos():
    """
    Verifica se existe algum modelo com uma versão mais nova. Se existir, informa para o Docker host que o container do
    Worker dever ser reiniciado.
    :return: 0, se os modelos possuem as mesmas versões; 1, caso contrário ou se acontecer algum erro.
    """
    if not Path.exists(Path("/tmp/runid_models.pkl")):
        LOGGER.error("O arquivo com as versões dos modelos não foi encontrado no caminho '/tmp/runid_models.pkl'")
        return 1

    modelos_desatualizados = []
    dados_modelos = convert_artifact_to_object(file_name="runid_models.pkl", path="/tmp")

    # Compara os run_ids dos modelos carregados pelo Worker com os modelos carregados para verificação e guarda os que
    # estão diferentes, ou seja, desatualizados
    for nome_modelo, versao_modelo in MODELOS_VERSOES.items():
        if versao_modelo != dados_modelos[nome_modelo]:
            modelos_desatualizados.append(nome_modelo)

    if modelos_desatualizados:
        LOGGER.warning(f"Os seguintes modelos foram atualizados e precisam ser recarregados: {modelos_desatualizados}")
        return 1
    else:
        LOGGER.info("Todos os modelos estão na versão mais atual, não é necessário recarregá-los!")
        return 0


if __name__ == "__main__":
    try:
        resultado = verificar_dados_modelos()
    except BaseException as e:
        LOGGER.error(f"Não foi possível realizar o health check do Worker. Erro: {e.__class__} - {e}", exc_info=True)
        exit(1)

    exit(resultado)
