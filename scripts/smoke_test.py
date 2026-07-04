"""
SupplyMind — Environment Smoke Test
Run this script to verify that all core libraries are installed
and your environment is ready for development.
"""

import sys
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def run_smoke_test():
    logger.info("Starting SupplyMind Smoke Test...")
    logger.info(f"Python Version: {sys.version.split()[0]}")

    # Core ML
    try:
        import numpy as np
        import pandas as pd
        import sklearn
        logger.info(f"✅ Core Data Stack OK (numpy {np.__version__}, pandas {pd.__version__}, sklearn {sklearn.__version__})")
    except ImportError as e:
        logger.error(f"❌ Core Data Stack failed: {e}")

    # Deep Learning & Transformers
    try:
        import torch
        from pytorch_forecasting import TemporalFusionTransformer
        logger.info(f"✅ PyTorch & Forecasting OK (torch {torch.__version__})")
    except ImportError as e:
        logger.error(f"❌ PyTorch Stack failed: {e}")

    # Gradient Boosting & Explainability
    try:
        import lightgbm as lgb
        import shap
        logger.info(f"✅ LightGBM & SHAP OK (lightgbm {lgb.__version__}, shap {shap.__version__})")
    except ImportError as e:
        logger.error(f"❌ LightGBM/SHAP Stack failed: {e}")

    # API & Backend
    try:
        import fastapi
        import sqlalchemy
        from pydantic import BaseModel
        logger.info(f"✅ FastAPI & Backend Stack OK (fastapi {fastapi.__version__}, sqlalchemy {sqlalchemy.__version__})")
    except ImportError as e:
        logger.error(f"❌ FastAPI Stack failed: {e}")

    # Agent & Orchestration
    try:
        import langchain
        import langgraph
        import importlib.metadata
        lg_ver = importlib.metadata.version("langgraph")
        logger.info(f"✅ Agentic AI Stack OK (langchain {langchain.__version__}, langgraph {lg_ver})")
    except ImportError as e:
        logger.error(f"❌ Agentic AI Stack failed: {e}")

    logger.info("=========================================")
    logger.info("Smoke test completed.")
    logger.info("If you see all ✅ marks, your environment is ready!")

if __name__ == "__main__":
    run_smoke_test()
