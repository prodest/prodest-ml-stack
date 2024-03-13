# -------------------------------------------------------------------------------------------------------------------
# Script responsável por fazer um health check para verificar se o Worker está com os modelos atualizados. Caso
# exista algum modelo desatualizado, coloca o container no estado 'unhealthy'.
# -------------------------------------------------------------------------------------------------------------------
import warnings
from mllibprodest.utils import make_log
from mllibprodest.initiators.model_initiator import InitModels as Im
from pathlib import Path

# Cria (ou abre) o arquivo de logs para o script e retorna o logger para geração dos logs
LOGGER = make_log("worker_pub_health_check.log")

LOGGER.info("[*] Instanciando o(s) modelo(s) de ML para realizar o health check do Worker...")
try:
    # Evita os warnings que estão atrapalhando a saida do script
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        MODELOS_CARREGADOS = Im.init_models()

    # Obtém um modelo qualquer para utilizar o método 'convert_artifact_to_object'
    MODELO_AUX = MODELOS_CARREGADOS[list(MODELOS_CARREGADOS.keys())[0]]
except BaseException as e:
    LOGGER.error(f"Não foi possível instanciar o(s) modelo(s). Mensagem do 'init_models': {e.__class__} - {e}",
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
    dados_modelos = MODELO_AUX.convert_artifact_to_object(model_name="", file_name="runid_models.pkl", path="/tmp")

    # Compara os run_ids dos modelos carregados pelo Worker com os modelos carregados para verificação e guarda os que
    # estão diferentes, ou seja, desatualizados
    for nome_modelo, modelo in MODELOS_CARREGADOS.items():
        if modelo.get_model_version() != dados_modelos[nome_modelo]:
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
