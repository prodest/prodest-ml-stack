#!/bin/bash
export MLFLOW_SERVER_ALLOWED_HOSTS="${MLFLOW_SERVER_ALLOWED_HOSTS:-localhost,127.0.0.1}"

mlflow db upgrade sqlite:///mlflow.db

mlflow server \
  --app-name basic-auth \
  --backend-store-uri sqlite:///mlflow.db \
  --host 0.0.0.0 \
  --allowed-hosts "$MLFLOW_SERVER_ALLOWED_HOSTS" \
  --default-artifact-root "$DEFAULT_ARTIFACT_ROOT"