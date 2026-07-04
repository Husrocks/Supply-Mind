# SupplyMind 🧠⛓️
### Predictive Supply Chain Disruption Intelligence with Autonomous Mitigation Orchestration

---

## What Is This?

SupplyMind is a graduate-level ML + Agentic AI platform that continuously monitors
thousands of suppliers and SKUs, predicts disruptions 2–4 weeks ahead of impact,
and autonomously executes mitigation actions (emergency POs, safety stock adjustments,
manager escalations) — with full human oversight and audit trails.

---

## Architecture at a Glance

```
DATA LAYER          →    ML MODELS           →    AGENT          →    DASHBOARD
─────────────────────────────────────────────────────────────────────────────────
M5 Sales (Kaggle)        TFT (Demand)             Orchestrator        React UI
DataCo Supply Chain      LightGBM (Supplier Risk) Policy Engine       D3.js Network
Synthetic Suppliers      LSTM AE (Anomaly)        Audit Logger        Recharts
FRED / ACLED             ─────────────────        ─────────────       Override Console
                         Risk Context Frame       Issue POs
                                                  Adjust Stock
                                                  Escalate
```

---

## Project Structure

```
supplymind/
├── data/
│   ├── raw/                  ← Downloaded datasets (not in git)
│   ├── processed/            ← Feature-engineered outputs
│   └── synthetic/            ← Generated supplier data
│
├── models/
│   ├── tft/                  ← Temporal Fusion Transformer
│   ├── lgbm/                 ← LightGBM supplier risk scorer
│   ├── lstm_ae/              ← LSTM Autoencoder anomaly detection
│   └── calibration/          ← Isotonic regression calibrators
│
├── agent/
│   ├── orchestrator.py       ← Main agent loop
│   ├── context_builder.py    ← Risk context frame assembly
│   ├── policy.py             ← Decision rules + tier logic
│   ├── actions.py            ← Action types (PO, stock, escalation)
│   ├── audit_logger.py       ← Full reasoning audit trail
│   └── triggers.py           ← Schedule / Event / Threshold triggers
│
├── api/
│   ├── main.py               ← FastAPI application entry point
│   ├── routes/               ← API route handlers
│   ├── schemas/              ← Pydantic request/response models
│   └── services/             ← Business logic layer
│
├── simulation/
│   └── supplier_sim.py       ← Synthetic supplier data generator
│
├── notebooks/                ← EDA and experimentation
├── scripts/                  ← Utility scripts (download, train, etc.)
├── tests/                    ← Unit & integration tests
├── frontend/                 ← React + TypeScript dashboard
└── docs/                     ← Architecture diagrams, API docs
```

---

## Quick Start

### 1. Clone and set up environment
```bash
git clone https://github.com/your-org/supplymind.git
cd supplymind

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure environment
```bash
copy .env.example .env
# Edit .env with your API keys and database credentials
```

### 3. Download datasets
```bash
# Set Kaggle credentials in .env first
python scripts/download_datasets.py
```

### 4. Generate synthetic supplier data
```bash
python simulation/supplier_sim.py --suppliers 1200 --weeks 104 --seed 42
```

### 5. Run API server
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Run smoke test
```bash
python scripts/smoke_test.py
```

---

## ML Models

| Model | Task | Algorithm | Primary Metric |
|-------|------|-----------|----------------|
| Demand Forecaster | Multi-horizon SKU demand | Temporal Fusion Transformer | WRMSSE |
| Supplier Risk Scorer | Binary disruption prediction | LightGBM + SHAP | PR-AUC |
| Anomaly Detector | Unsupervised lead time anomaly | LSTM Autoencoder | F1 @ threshold |

---

## Agent Decision Tiers

| Tier | Condition | Agent Action |
|------|-----------|-------------|
| **Tier 1 — Autonomous** | Cost ≤ $85k + risk ≥ 0.75 + reversible | Execute + notify |
| **Tier 2 — Recommend** | Cost > $85k OR new supplier | Prepare card, await approval |
| **Tier 3 — Escalate** | Cascade failure OR low confidence | Surface context, defer to human |

---

## Datasets Used

| Dataset | Source | Purpose |
|---------|--------|---------|
| M5 Forecasting | Kaggle | Demand forecasting (TFT) |
| DataCo Smart Supply Chain | Kaggle | Supplier feature engineering |
| Supply Chain Analysis (Fashion) | Kaggle | Defect/lead time features |
| USAID Shipment Data | Kaggle/USAID | Delivery label ground truth |
| Synthetic Supplier Dataset | Generated | LightGBM + LSTM AE training |
| FRED Economic Data | fredapi | Macro risk signals |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| ML Framework | PyTorch, pytorch-forecasting, LightGBM |
| Experiment Tracking | MLflow |
| Agent Framework | LangGraph + APScheduler + Kafka |
| Backend API | FastAPI + PostgreSQL + Redis |
| Frontend | React + TypeScript + D3.js + Recharts |
| Deployment | Docker Compose |

---

## Academic Context

- **Demand forecasting:** Lim et al. (2020) — Temporal Fusion Transformers (NeurIPS)
- **Explainability:** Lundberg & Lee (2017) — SHAP (NeurIPS)
- **Tabular ML:** Shwartz-Ziv & Armon (2022) — Deep Learning vs. Gradient Boosting
- **Calibration:** Guo et al. (2017) — On Calibration of Modern Neural Networks
- **Dataset:** Makridakis et al. (2022) — M5 accuracy competition
