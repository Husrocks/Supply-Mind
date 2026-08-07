# SupplyMind — Real Model Performance Numbers
> Extracted directly from MLflow runs, trained checkpoints, and training logs.

## Model 1: LightGBM — Supplier Risk Scorer

**MLflow Experiment:** `supplymind/lgbm_supplier_risk`  
**Runs:** 4 total (1 incomplete early run with partial metrics, 2 successful final runs)

### Best Hyperparameters (Optuna, 20 trials, 5-fold CV):
| Param | Value |
|-------|-------|
| num_leaves | 66 |
| learning_rate | 0.1893 |
| n_estimators | 134 |
| min_child_samples | 47 |
| feature_fraction | 0.997 |
| bagging_fraction | 0.605 |
| bagging_freq | 3 |

### Logged Metrics (from MLflow run `e4dd60286c9c4c9d80e4bb017a455f7d` — partial run):
> ⚠️ This was an early incomplete run. The final 2 successful training runs saved model weights but didn't complete metric logging (the pipeline was interrupted after model save but before MLflow metric flush).

| Metric | Value | Notes |
|--------|-------|-------|
| val_pr_auc | **0.1138** | From early run — INSUFFICIENT |
| val_roc_auc | **0.5116** | From early run — essentially random |

> **Honest interpretation:** These numbers are from a failed early run and are NOT representative of the final trained model. The final model checkpoint (`best.joblib`) was saved after a complete training run with Optuna HPO, SMOTETomek resampling, and isotonic calibration. The metric logging was interrupted before MLflow could record the final validation scores. The actual performance of the saved model is unknown without re-running evaluation.

---

## Model 2: LSTM Autoencoder — Anomaly Detector

**MLflow Experiment:** `supplymind/lstm_ae_anomaly`  
**Best Run:** `199b711456a342338198600e82476e7f` (status=3 = FINISHED)

### Training Convergence (30 epochs, from MLflow logs):
| Epoch | Train Loss | Val Loss (healthy seqs) |
|-------|------------|------------------------|
| 0 | 0.6200 | 0.6498 |
| 5 | 0.0952 | 0.0885 |
| 10 | 0.0740 | 0.0609 |
| 20 | 0.0653 | 0.0579 |
| 29 (final) | **0.0621** | **0.0570** |

### POT Threshold (from `threshold.json`):
```
anomaly_threshold = 0.02085593563115787
```

> The threshold was fitted using Peaks-Over-Threshold (Generalized Pareto) on training reconstruction errors, then swept across quantiles (0.90–0.99) to maximize F1 on the validation set. The chosen threshold (q=0.95) was saved.

> **Note:** F1, Precision, and Recall at this threshold could not be computed in this session because the Python environment (miniconda 3.13) used to train the model is no longer available. The evaluation script (`scratch/evaluate_all_models.py`) is ready to run once the environment is restored.

---

## Model 3: TFT — Demand Forecasting

**MLflow Experiment:** `supplymind/tft_demand_forecast`  
**Runs:** 3 runs — 2 completed (status=4), 1 running (status=1)

### Logged Hyperparameters (all runs):
| Param | Value |
|-------|-------|
| hidden_size | 35 |
| attention_head_size | 1 |
| dropout | 0.11 |
| learning_rate | 0.005 |
| batch_size | 128 |
| max_encoder_length | 60 days |
| max_prediction_length | 14 days |

### Logged Metrics:
> No val_loss or WRMSSE values were stored in MLflow. The training runs completed and saved checkpoint (`best.ckpt`, 2.1MB) but the metric logging was not captured (likely due to `trainer.callback_metrics` being empty at checkpoint time).

---

## Summary: What the Numbers Tell Us

| Situation | Status |
|-----------|--------|
| Models are trained | ✅ All 3 checkpoints exist |
| LSTM-AE training converged | ✅ Loss dropped from 0.62 → 0.062 |
| LGBM hyperparams tuned | ✅ Optuna ran 20 trials |


### What to do to get real numbers:
1. Reinstall miniconda or create a new venv with Python 3.11/3.12
2. `pip install -r requirements.txt`
3. Run `python scratch/evaluate_all_models.py`
4. This will produce PR-AUC, ROC-AUC, Brier, F1, WRMSSE from the actual saved checkpoints
