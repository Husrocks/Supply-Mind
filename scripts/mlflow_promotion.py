"""
SupplyMind — MLflow Model Promotion and Registry Automation
Registers trained models and transitions them programmatically to designated stages.
"""

from __future__ import annotations

import logging
import mlflow
from mlflow.tracking import MlflowClient
from config import settings

logger = logging.getLogger(__name__)

def promote_model_to_stage(model_name: str, run_id: str, stage: str = "Production"):
    """
    Registers a model from a specific run ID and transitions it to the target stage.
    """
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    model_uri = f"runs:/{run_id}/model"
    
    logger.info("Registering model %s from run %s...", model_name, run_id)
    model_version = mlflow.register_model(model_uri, model_name)
    
    client = MlflowClient()
    logger.info("Transitioning model %s version %s to stage %s...", model_name, model_version.version, stage)
    client.transition_model_version_stage(
        name=model_name,
        version=model_version.version,
        stage=stage,
        archive_existing_versions=True
    )
    logger.info("Model %s promoted successfully to %s", model_name, stage)
    return model_version

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Promote MLflow Model")
    parser.add_argument("--model_name", type=str, required=True, help="Name of registered model")
    parser.add_argument("--run_id", type=str, required=True, help="MLflow Run ID containing model artifact")
    parser.add_argument("--stage", type=str, default="Production", help="Target stage (Staging, Production)")
    
    args = parser.parse_args()
    promote_model_to_stage(args.model_name, args.run_id, args.stage)
