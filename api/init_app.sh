#!/bin/bash
# Apaga o arquivo de erro para liberar para o health check ser executado novamente sem erro
rm -f /tmp/error_8EDo2OWK9Sd7A4aN0uni.err

# Inicia a aplicação
uvicorn main:app --host 0.0.0.0 --reload
