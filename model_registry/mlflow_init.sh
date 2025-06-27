#!/bin/bash
mlflow db upgrade sqlite:///mlflow.db
mlflow server --app-name basic-auth --backend-store-uri sqlite:///mlflow.db --host 0.0.0.0 --default-artifact-root $DEFAULT_ARTIFACT_ROOT
