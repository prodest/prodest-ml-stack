# ----------------------------------------------------------------------------------------------------
# Script para automatização do retreino dos modelos
# ----------------------------------------------------------------------------------------------------
from mllibprodest.initiators.model_initiator import InitModels as Im
from mllibprodest.utils import make_log

# Códigos para impressão de mensagens coloridas no terminal
RED = "\033[1;31m"
GREEN = "\033[0;32m"
RESET = "\033[0;0m"

# Cria (ou abre) o arquivo de logs para o worker e retorna o logger para geração dos logs
LOGGER = make_log("worker_retrain.log")


def retreino(modelos: dict):
    """
    Faz o retreino dos modelos, caso seja necessário.
        :param modelos: Dicionário contendo os modelos carregados.
                        Exemplo: {'NOME_DO_MODELO': <models.retrain1.ModeloRETRAIN object at 0x7f70045bf1f0>}
    """
    LOGGER.info("*************************** RETREINO DO(S) MODELO(S) ***************************")

    for nome_modelo, modelo in modelos.items():
        LOGGER.info(f">> ModeloRETRAIN - {nome_modelo}:")

        try:
            # Obtém os valores dos parâmetros e datasets necessários para a avaliação/retreino
            model_name = modelo.get_model_name()
            provider_modelo = modelo.get_model_provider_name()
            datasets_names = modelo.load_production_datasets_names(model_name=model_name, provider=provider_modelo)
            experiment_name = modelo.get_experiment_name()
            dataset_provider = modelo.get_dataset_provider_name()
            baseline_metrics = modelo.load_production_baseline(model_name=model_name, provider=provider_modelo)
            model_params = modelo.load_production_params(model_name=model_name, provider=provider_modelo)
        except BaseException as e:
            msg = f"Não foi possível obter todos os parâmetros do modelo que está em produção: {e.__class__} - {e}"
            LOGGER.error(msg, exc_info=True)
            print(f"\n{RED}FALHA NO RETREINO: Verifique as mensagens de erro para mais detalhes!{RESET}\n")
            raise e

        # Valida alguns tipos de retorno esperados
        tipo_datasets_names = type(datasets_names)

        if tipo_datasets_names is not dict:
            msg = f"O retorno da função 'load_production_datasets_names' está incorreto. Deveria ser 'dict', mas foi " \
                  f"retornado '{tipo_datasets_names.__name__}'"
            LOGGER.error(msg)
            print(f"\n{RED}FALHA NO RETREINO: Verifique as mensagens de erro para mais detalhes!{RESET}\n")
            exit(1)

        tipo_baseline_metrics = type(baseline_metrics)

        if tipo_baseline_metrics is not dict:
            msg = f"O retorno da função 'load_production_baseline' está incorreto. Deveria ser 'dict', mas foi " \
                  f"retornado '{tipo_baseline_metrics.__name__}'"
            LOGGER.error(msg)
            print(f"\n{RED}FALHA NO RETREINO: Verifique as mensagens de erro para mais detalhes!{RESET}\n")
            exit(1)

        tipo_model_params = type(model_params)

        if tipo_model_params is not dict:
            msg = f"O retorno da função 'load_production_params' está incorreto. Deveria ser 'dict', mas foi " \
                  f"retornado '{tipo_model_params.__name__}'"
            LOGGER.error(msg)
            print(f"\n{RED}FALHA NO RETREINO: Verifique as mensagens de erro para mais detalhes!{RESET}\n")
            exit(1)

        LOGGER.info(f"**** Rodando para os datasets: {datasets_names} ****")

        try:
            # Avaliação para verificar se o modelo precisa ser retreinado
            modelo_carregado = modelo.load_model(model_name=model_name, provider=provider_modelo)
            datasets = modelo.load_datasets(datasets_filenames=datasets_names, provider=dataset_provider)
            necessita_retreino, info = modelo.evaluate(model=modelo_carregado, datasets=datasets,
                                                       baseline_metrics=baseline_metrics,
                                                       training_params=model_params, artifacts_path="temp_area",
                                                       batch_size=10000)
        except BaseException as e:
            msg = f"Não foi possível fazer a avaliação do modelo: {e.__class__} - {e}"
            LOGGER.error(msg, exc_info=True)
            print(f"\n{RED}FALHA NO RETREINO: Verifique as mensagens de erro para mais detalhes!{RESET}\n")
            raise e

        tipo_necessita_retreino = type(necessita_retreino)
        tipo_info = type(info)

        if tipo_necessita_retreino is not bool or tipo_info is not dict:
            msg = f"O retorno da função 'evaluate' está incorreto. Deveria ser ('bool', 'dict'), mas foi retornado " \
                  f"('{tipo_necessita_retreino.__name__}', '{tipo_info.__name__}')"
            LOGGER.error(msg)
            print(f"\n{RED}FALHA NO RETREINO: Verifique as mensagens de erro para mais detalhes!{RESET}\n")
            exit(1)

        # Retreina o modelo, caso necessite
        if necessita_retreino:
            LOGGER.info(f"O modelo necessita ser retreinado. Motivo: {info}")

            try:
                # Tentei liberar a memória utilizada pelo modelo (carregado na avaliação acima) de outra forma e não
                # consegui. Só consegui liberar recarregando o modelo! Pode ser por conta de algum cache do MLflow...
                modelo.load_model(model_name=model_name, provider=provider_modelo)

                # A carga precisa ser refeita porque o conteúdo dos datasets carregados anteriormente foi consumido
                datasets = modelo.load_datasets(datasets_filenames=datasets_names, provider=dataset_provider)

                modelo.retrain(production_model_name=model_name, production_params=model_params,
                               experiment_name=experiment_name, datasets=datasets, reasons=info)
            except BaseException as e:
                msg = f"Não foi possível retreinar o modelo: {e.__class__} - {e}"
                LOGGER.error(msg, exc_info=True)
                print(f"\n{RED}FALHA NO RETREINO: Verifique as mensagens de erro para mais detalhes!{RESET}\n")
                raise e

            LOGGER.info(f"O modelo foi retreinado utilizando os parâmetros: {model_params}")
        else:
            LOGGER.info(f"O modelo NÃO necessita ser retreinado. Informações adicionais: {info}")


if __name__ == "__main__":
    modelos = None

    # Instancia o(s) modelo(s) para avaliação/realização do retreino
    try:
        modelos = Im.init_models()
    except BaseException as e:
        msg = f"Não foi possível instanciar o(s) modelo(s): {e.__class__} - {e}"
        LOGGER.error(msg, exc_info=True)
        print(f"\n{RED}FALHA NO RETREINO: Verifique as mensagens de erro para mais detalhes!{RESET}\n")
        raise e

    retreino(modelos)
