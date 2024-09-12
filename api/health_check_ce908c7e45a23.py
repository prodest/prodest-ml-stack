# -------------------------------------------------------------------------------------------------------------------
# Script responsável por fazer health check para verificar se a API está funcionando corretamente. Caso contrário,
# coloca o container no estado 'unhealthy'.
# -------------------------------------------------------------------------------------------------------------------
import logging
from pathlib import Path


def make_log() -> logging.Logger:
    """
    Cria um logger para gerar logs na console.
        :return: Um logger para geração dos logs.
    """
    # Configurações básicas
    logging.basicConfig(level=logging.CRITICAL)
    logger = logging.getLogger("API_HEALTH_CHECK")
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


def health_check():
    """
    Verifica se há um arquivo de erro. Caso positivo, retorna falha para o health check do container.
    """
    if not Path.exists(Path("/tmp/error_8EDo2OWK9Sd7A4aN0uni.err")):
        LOGGER.info("A API está rodando corretamente!")
        exit(0)
    else:
        LOGGER.error("A API está com problema. Se persistir, analise os logs para tentar identificar a causa!")
        exit(1)


if __name__ == "__main__":
    health_check()
