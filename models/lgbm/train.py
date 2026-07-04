"""
SupplyMind — LightGBM Supplier Risk Model
Trains a calibrated binary classifier on the engineered supplier dataset.

Pipeline:
  1. Load processed train/val/test parquet datasets
  2. Optuna hyperparameter search (30 trials) using train cross-validation
  3. Final model on full training set with best params
  4. Post-hoc isotonic calibration on validation set
  5. Save best calibrated model and log feature importance
"""

from __future__ import annotations

import os
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"

import sys
import logging
from pathlib import Path

import joblib
import mlflow
import mlflow.lightgbm
import numpy as np
import optuna
import pandas as pd
from imblearn.combine import SMOTETomek
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import LabelEncoder
import lightgbm as lgb

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from config import settings

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path(settings.lgbm_model_path).parent
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

CATEGORICAL_FEATURES = ["country", "contract_tier"]

NUMERIC_FEATURES = [
    "tenure_years",
    "prev_otd",
    "prev_lead_time",
    "prev_po_accept",
    "otd_mean_4w",
    "otd_mean_12w",
    "lead_time_mean_4w",
    "lead_time_std_4w",
    "lead_time_mean_12w",
    "po_accept_mean_4w",
    "lead_time_slope_6w"
]

# Monotonic constraints for supplier risk: positional list aligned to
# NUMERIC_FEATURES + CATEGORICAL_FEATURES column order.
# +1  = feature value increasing can only INCREASE predicted disruption risk
# -1  = feature value increasing can only DECREASE predicted disruption risk
#  0  = unconstrained
#
# Column order: tenure_years, prev_otd, prev_lead_time, prev_po_accept,
#               otd_mean_4w, otd_mean_12w, lead_time_mean_4w, lead_time_std_4w,
#               lead_time_mean_12w, po_accept_mean_4w, lead_time_slope_6w,
#               country (cat), contract_tier (cat)
MONOTONE_CONSTRAINTS = [
    0,   # tenure_years         — longer tenure is generally better but not monotone
    -1,  # prev_otd             — higher OTD rate → lower disruption risk
    0,   # prev_lead_time       — not strictly monotone (longer lead time can be planned)
    0,   # prev_po_accept       — higher acceptance good but not strictly monotone
    0,   # otd_mean_4w          — short window noisy
    -1,  # otd_mean_12w         — higher 12-week OTD → lower disruption risk (stable signal)
    0,   # lead_time_mean_4w    — short window noisy
    0,   # lead_time_std_4w     — variance directional but interaction-dependent
    0,   # lead_time_mean_12w   — longer lead time is double-edged
    0,   # po_accept_mean_4w    — noisy window
    +1,  # lead_time_slope_6w   — worsening slope (positive) → higher disruption risk
    0,   # country (categorical, encoded int)
    0,   # contract_tier (categorical, encoded int)
]

TARGET = "disruption_flag"

def load_and_prepare(path: str | Path, encoders: dict[str, LabelEncoder] | None = None) -> tuple[pd.DataFrame, pd.Series, dict[str, LabelEncoder]]:
    """Load parquet, encode categoricals using specified encoders or fit new ones, and return (X, y, encoders)."""
    df = pd.read_parquet(path)
    
    out_encoders = {}
    # Encode categoricals
    for col in CATEGORICAL_FEATURES:
        if encoders and col in encoders:
            le = encoders[col]
            classes_set = set(le.classes_)
            df[col] = df[col].astype(str).map(
                lambda val: int(le.transform([val])[0]) if val in classes_set else -1
            )
            out_encoders[col] = le
        else:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            out_encoders[col] = le
        
    all_features = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    X = df[all_features].copy()
    y = df[TARGET].astype(int)
    
    return X, y, out_encoders

def _objective(trial: optuna.Trial, X_train_raw: np.ndarray, y_train_raw: np.ndarray, cat_indices: list[int]) -> float:
    """Cross-validated PR-AUC objective for Optuna (resampling only train folds)."""
    params = {
        "objective": "binary",
        "metric": "average_precision",
        "verbosity": -1,
        "boosting_type": "gbdt",
        "num_leaves": trial.suggest_int("num_leaves", 31, 128),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        "min_child_samples": trial.suggest_int("min_child_samples", 10, 50),
        "feature_fraction": trial.suggest_float("feature_fraction", 0.6, 1.0),
        "bagging_fraction": trial.suggest_float("bagging_fraction", 0.6, 1.0),
        "bagging_freq": trial.suggest_int("bagging_freq", 1, 5),
        "n_estimators": trial.suggest_int("n_estimators", 100, 500),
        "monotone_constraints": MONOTONE_CONSTRAINTS,
    }

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = []
    smt = SMOTETomek(random_state=42)
    for fold_train_idx, fold_val_idx in skf.split(X_train_raw, y_train_raw):
        X_f_tr_raw, y_f_tr_raw = X_train_raw[fold_train_idx], y_train_raw[fold_train_idx]
        X_f_val, y_f_val = X_train_raw[fold_val_idx], y_train_raw[fold_val_idx]

        # Resample only the training fold to prevent validation leakage
        X_f_tr, y_f_tr = smt.fit_resample(X_f_tr_raw, y_f_tr_raw)

        model = lgb.LGBMClassifier(**params)
        model.fit(
            X_f_tr, y_f_tr,
            eval_set=[(X_f_val, y_f_val)],
            categorical_feature=cat_indices,
            callbacks=[lgb.early_stopping(30, verbose=False)]
        )
        proba = model.predict_proba(X_f_val)[:, 1]
        scores.append(average_precision_score(y_f_val, proba))

    return float(np.mean(scores))

def train(n_trials: int = 20, experiment_name: str | None = None) -> Path:
    """Full training pipeline using pre-split processed datasets."""
    exp_name = experiment_name or f"{settings.mlflow_experiment_name}/lgbm_supplier_risk"

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(exp_name)

    # Load pre-split datasets
    train_path = Path(settings.data_processed_dir) / "supplier_train.parquet"
    val_path = Path(settings.data_processed_dir) / "supplier_val.parquet"
    
    logger.info("Loading pre-split training and validation sets...")
    X_train_raw, y_train_raw, encoders = load_and_prepare(train_path)
    X_val, y_val, _ = load_and_prepare(val_path, encoders=encoders)
    
    cat_indices = [X_train_raw.columns.get_loc(c) for c in CATEGORICAL_FEATURES]

    # Validate that monotone_constraints is aligned to the feature matrix
    n_features = X_train_raw.shape[1]
    assert len(MONOTONE_CONSTRAINTS) == n_features, (
        f"MONOTONE_CONSTRAINTS length ({len(MONOTONE_CONSTRAINTS)}) must equal "
        f"X_train_raw.shape[1] ({n_features}). Update MONOTONE_CONSTRAINTS to match "
        f"the column order of NUMERIC_FEATURES + CATEGORICAL_FEATURES."
    )
    logger.info(
        "Monotone constraints validated: %d features, %d constraints",
        n_features, len(MONOTONE_CONSTRAINTS),
    )

    with mlflow.start_run(run_name="lgbm_training") as run:
        logger.info(f"Starting Optuna HPO with {n_trials} trials...")
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
        study.optimize(
            lambda trial: _objective(trial, X_train_raw.values, y_train_raw.values, cat_indices),
            n_trials=n_trials
        )

        best_params = study.best_params
        logger.info(f"Best CV PR-AUC: {study.best_value:.4f}")
        mlflow.log_params(best_params)

        # Train final model
        logger.info("Training final model with monotone_constraints...")
        final_params = {
            **best_params,
            "objective": "binary",
            "verbosity": -1,
            "monotone_constraints": MONOTONE_CONSTRAINTS,
        }
        
        # Fit on resampled full training set
        smt_full = SMOTETomek(random_state=42)
        X_train_res, y_train_res = smt_full.fit_resample(X_train_raw.values, y_train_raw.values)
        
        final_model = lgb.LGBMClassifier(**final_params)
        final_model.fit(X_train_res, y_train_res, categorical_feature=cat_indices)

        # Post-hoc calibration using validation set
        logger.info("Calibrating probabilities...")
        calibrated = CalibratedClassifierCV(estimator=final_model, cv="prefit", method="isotonic")
        calibrated.fit(X_val.values, y_val.values)

        # Evaluate on validation set
        proba_val = calibrated.predict_proba(X_val.values)[:, 1]
        val_pr_auc = average_precision_score(y_val, proba_val)
        val_roc_auc = roc_auc_score(y_val, proba_val)
        
        logger.info(f"Validation PR-AUC: {val_pr_auc:.4f} | ROC-AUC: {val_roc_auc:.4f}")
        mlflow.log_metrics({"val_pr_auc": val_pr_auc, "val_roc_auc": val_roc_auc})

        # Calibration Curve & Brier Score
        from sklearn.metrics import brier_score_loss
        from sklearn.calibration import calibration_curve
        import matplotlib.pyplot as plt

        brier = brier_score_loss(y_val, proba_val)
        logger.info(f"Validation Brier Score: {brier:.4f}")
        mlflow.log_metric("val_brier_score", brier)

        prob_true, prob_pred = calibration_curve(y_val, proba_val, n_bins=10)
        plt.figure(figsize=(6, 6))
        plt.plot(prob_pred, prob_true, marker='o', label="Calibrated LGBM")
        plt.plot([0, 1], [0, 1], linestyle='--', label="Perfectly Calibrated")
        plt.title(f"LGBM Calibration (Brier: {brier:.4f})")
        plt.xlabel("Predicted Probability")
        plt.ylabel("True Probability")
        plt.legend()
        plot_path = CHECKPOINT_DIR / "calibration_curve.png"
        plt.savefig(plot_path)
        plt.close()
        mlflow.log_artifact(str(plot_path))
        logger.info("Saved calibration curve plot to MLflow artifacts")

        # Save model along with LabelEncoder mappings
        ckpt_path = CHECKPOINT_DIR / "best.joblib"
        joblib.dump({
            "model": calibrated,
            "feature_names": X_train_raw.columns.tolist(),
            "encoders": encoders
        }, ckpt_path)
        logger.info(f"Saved model to {ckpt_path}")
        
    return ckpt_path

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    train(n_trials=15)


