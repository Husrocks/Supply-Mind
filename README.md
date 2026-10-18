# 🧠 SupplyMind ⛓️

**Predictive Supply Chain Disruption Intelligence with Autonomous Mitigation Orchestration**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

---

## 📖 What is SupplyMind?

SupplyMind is a graduate-level ML and Agentic AI platform designed for the modern supply chain. It continuously monitors thousands of suppliers and SKUs, predicts potential disruptions 2–4 weeks ahead of impact, and autonomously executes mitigation actions—such as placing emergency POs, adjusting safety stock, or escalating to human managers—while maintaining a comprehensive audit trail.

This system is built to balance autonomous operational efficiency with strict human oversight and accountability boundaries.

---

## ✨ Key Features

- **Demand Forecasting:** Utilizes Temporal Fusion Transformers (TFT) to predict multi-horizon SKU demand.
- **Supplier Risk Scoring:** Leverages LightGBM & SHAP to calculate the probability of disruptions.
- **Anomaly Detection:** Employs LSTM Autoencoders to flag unusual lead times or supplier behavior.
- **Autonomous Agentic Orchestration:** Operates across three distinct decision tiers based on financial thresholds and confidence scores.
- **Explainability First:** Every automated action generates an Action Card detailing the exact "why" behind the decision (SHAP drivers, anomaly flags, confidence scores).

---

## 🏛 Architecture at a Glance

The architecture connects raw data inputs to complex ML models, managed by a LangGraph-based agent orchestrator, and surfaced through a responsive React dashboard.

```text
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

## 🚀 Quick Start

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/your-org/supplymind.git
cd supplymind

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/Mac:
source .venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 2. Configuration

Copy the example environment file and fill in your API keys and credentials:
```bash
cp .env.example .env
```

### 3. Prepare the Data

Set your Kaggle credentials in the `.env` file first, then run:

```bash
# Download Kaggle datasets
python scripts/download_datasets.py

# Generate synthetic supplier data for testing
python simulation/supplier_sim.py --suppliers 1200 --weeks 104 --seed 42
```

### 4. Run the Application

```bash
# Start the API server (scoped reload prevents database writes from restarting the server)
uvicorn api.main:app --reload --reload-dir api --reload-dir agent --reload-dir models --host 0.0.0.0 --port 8000
# Alternatively on Windows PowerShell: .\scripts\dev_server.ps1
# Alternatively on Linux/macOS: ./scripts/dev_server.sh
```

### 5. Verify the Setup

```bash
# Run the built-in smoke test
python scripts/smoke_test.py
```

---

## 📚 Documentation & Guides

For more deep-dive information about how SupplyMind works under the hood, refer to these documents:

- [How This System Works](HOW_THIS_SYSTEM_WORKS.md): A plain-English explanation of the data, the AI agent's logic, and what is automated vs. manual.
- [Verify It Works](VERIFY_IT_WORKS.md): Detailed verification testing logic.
- [Design Guide](Design.md): UI/UX guidelines and styling tokens.

---

## 🤝 Contributing

We welcome contributions from the community—whether it's improving the ML models, enhancing the UI, fixing bugs, or writing documentation!

Please read our [Contributing Guidelines](CONTRIBUTING.md) to understand the workflow, from setting up your development environment to submitting a Pull Request.

---

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
