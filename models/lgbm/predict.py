"""
SupplyMind — LightGBM Supplier Risk Predictor
Loads the trained model, calibrator, and SHAP explainer for real-time inference.
"""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
import pandas as pd
import numpy as np

try:
    import shap
except (ImportError, OSError):
    shap = None

try:
    import lightgbm as lgb
except (ImportError, OSError):
    lgb = None

from pydantic import BaseModel, Field

from config import settings

logger = logging.getLogger(__name__)

# ── Feature definitions (must match training exactly) ──────────────────────────
CATEGORICAL_FEATURES = ["country", "contract_tier"]
NUMERIC_FEATURES = [
    "tenure_years", "prev_otd", "prev_lead_time", "prev_po_accept",
    "otd_mean_4w", "otd_mean_12w", "lead_time_mean_4w", "lead_time_std_4w",
    "lead_time_mean_12w", "po_accept_mean_4w", "lead_time_slope_6w",
]
TARGET = "disruption_flag"
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


class SupplierRiskPrediction(BaseModel):

    supplier_id: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_level: str
    shap_drivers: list[dict]

class RiskPredictor:
    def __init__(self, model_path: str | Path | None = None):
        self.model_path = Path(model_path or settings.lgbm_model_path)
        self.calibrated_model = None
        self.lgbm_estimator = None
        self.feature_names = []
        self.explainer = None
        self._load_model()

    def _load_model(self):
        """Load calibrated model and initialize SHAP."""
        if not self.model_path.exists():
            logger.warning("LightGBM Model checkpoint not found: %s. Operating in heuristic fallback mode.", self.model_path)
            self.calibrated_model = None
            return
            
        logger.info("Loading LightGBM risk model from %s", self.model_path)
        data = joblib.load(self.model_path)
        self.calibrated_model = data["model"]
        self.feature_names = data["feature_names"]
        self.encoders = data.get("encoders", {})
        
        # Extract underlying LGBM model for SHAP
        estimator = self.calibrated_model.estimator
        if hasattr(estimator, "estimator"):
            self.lgbm_estimator = estimator.estimator
        else:
            self.lgbm_estimator = estimator
        self.explainer = shap.TreeExplainer(self.lgbm_estimator)

    def predict(self, df: pd.DataFrame) -> list[SupplierRiskPrediction]:
        """
        Predict risk for a batch of suppliers and return structured predictions
        with top 3 SHAP feature drivers.
        """
        if self.calibrated_model is None:
            preds: list[SupplierRiskPrediction] = []
            for _, row in df.iterrows():
                sid = str(row.get("supplier_id", "SUP-0001"))
                otd = float(row.get("otd_mean_4w", row.get("prev_otd", 0.90)))
                lt_var = float(row.get("lead_time_std_4w", 1.0))
                score = round(max(0.02, min(0.98, (1.0 - otd) * 0.70 + (lt_var / 10.0) * 0.30)), 3)
                level = "CRITICAL" if score >= 0.75 else "HIGH" if score >= 0.50 else "MEDIUM" if score >= 0.25 else "LOW"
                preds.append(SupplierRiskPrediction(
                    supplier_id=sid,
                    risk_score=score,
                    risk_level=level,
                    shap_drivers=[
                        {"feature": "otd_mean_4w", "value": round(otd, 2), "impact": round(1.0 - otd, 3), "direction": "increases_risk" if otd < 0.85 else "decreases_risk"},
                        {"feature": "lead_time_std_4w", "value": round(lt_var, 2), "impact": round(lt_var / 10.0, 3), "direction": "increases_risk" if lt_var > 2.0 else "decreases_risk"}
                    ]
                ))
            return preds

        df_pred = df[self.feature_names].copy()

        # Label-encode categoricals using cached encoders (with fallback for unseen categories)
        for col in CATEGORICAL_FEATURES:
            if col in df_pred.columns:
                if col in self.encoders:
                    le = self.encoders[col]
                    classes_set = set(le.classes_)
                    df_pred[col] = df_pred[col].astype(str).map(
                        lambda val: int(le.transform([val])[0]) if val in classes_set else -1
                    )
                else:
                    from sklearn.preprocessing import LabelEncoder
                    le = LabelEncoder()
                    df_pred[col] = le.fit_transform(df_pred[col].astype(str))

        X = df_pred.reset_index(drop=True)

        # 1. Predict probabilities
        probabilities = self.calibrated_model.predict_proba(X)[:, 1]

        # 2. Get SHAP values
        shap_values = self.explainer.shap_values(X)
        if isinstance(shap_values, list):
            # For some LGBM versions, shap_values is a list [class_0, class_1]
            shap_values = shap_values[1]

        # 3. Assemble results
        results = []
        df_reset = df.reset_index(drop=True)
        for i in range(len(df_reset)):
            row = df_reset.iloc[i]
            sup_id = row.get("supplier_id", f"UNKNOWN_{i}")
            score = float(probabilities[i])

            # Risk Level
            if score >= settings.risk_critical_threshold:
                level = "CRITICAL"
            elif score >= settings.risk_high_threshold:
                level = "HIGH"
            elif score >= 0.50:
                level = "ELEVATED"
            else:
                level = "NORMAL"

            # Top 3 SHAP drivers
            instance_shap = shap_values[i]
            top_indices = np.argsort(np.abs(instance_shap))[-3:][::-1]

            drivers = []
            for idx in top_indices:
                feature_name = self.feature_names[idx]
                feat_val = X.iloc[i][feature_name]
                shap_val = float(instance_shap[idx])
                
                # Categorical values should remain as string, numeric as float
                if feature_name in CATEGORICAL_FEATURES:
                    val_parsed = str(feat_val)
                else:
                    try:
                        val_parsed = float(feat_val)
                    except (ValueError, TypeError):
                        val_parsed = str(feat_val)

                drivers.append({
                    "feature": feature_name,
                    "value": val_parsed,
                    "impact": shap_val,
                    "direction": "increases_risk" if shap_val > 0 else "decreases_risk"
                })

            pred = SupplierRiskPrediction(
                supplier_id=str(sup_id),
                risk_score=score,
                risk_level=level,
                shap_drivers=drivers
            )
            results.append(pred)

        return results

# Singleton instance
_predictor = None

def get_predictor() -> RiskPredictor:
    global _predictor
    if _predictor is None:
        _predictor = RiskPredictor()
    return _predictor

if __name__ == "__main__":
    # Test inference
    import numpy as np
    logging.basicConfig(level=logging.INFO)
    try:
        predictor = get_predictor()
        # Mock data based on train.py features
        mock_data = {feat: [0.0] for feat in predictor.feature_names}
        mock_data["supplier_id"] = ["TEST-01"]
        df_test = pd.DataFrame(mock_data)
        res = predictor.predict(df_test)
        print(res[0].model_dump_json(indent=2))
    except FileNotFoundError:
        print("Model not trained yet. Run train.py first.")
