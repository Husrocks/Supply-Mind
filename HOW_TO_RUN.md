# How to Run SupplyMind

Follow these exact, step-by-step instructions to get the complete SupplyMind agentic system running from a completely fresh clone.

## Prerequisites
*   Python 3.10+
*   Git

## Step-by-Step Setup

### 1. Clone the Repository & Setup Environment
Open your terminal and run:
```bash
git clone https://github.com/your-org/supplymind.git
cd supplymind

# Create a fresh virtual environment
python -m venv .venv

# Activate it (Windows)
.venv\Scripts\activate
# Activate it (Mac/Linux)
# source .venv/bin/activate

# Install all required packages
pip install -r requirements.txt
```

### 2. Configure the Environment
We need to set up the configuration variables. The default `.env.example` points to a local SQLite database, which is perfect for a fast demo.
```bash
# Windows
copy .env.example .env
# Mac/Linux
# cp .env.example .env
```
*(No further edits to `.env` are required for the local demo; it defaults to SQLite which requires no setup).*

### 3. Initialize the Database
Run the Alembic migrations to create all database tables in the local SQLite database (`supplymind.db`):
```bash
alembic upgrade head
```

### 4. Seed the Deterministic Demo Scenario
Because the system is driven by machine learning predictions over massive random datasets, a fresh run might not naturally trigger a high-risk scenario immediately. 

Run the seed script to deliberately inject `DEMO-SUP-001` (a high-risk supplier) and `DEMO-SKU-001` (a high-demand SKU with critically low inventory) into the datasets and database:
```bash
python scripts/seed_demo.py
```

### 5. Precompute ML Predictions
The system caches ML predictions for speed. Run the precomputation script so the agent immediately "perceives" the risk we just seeded:
```bash
python scripts/precompute_data.py
```
*Expected Output:* You should see logs confirming "Supplier risk precomputations complete" and "SKU demand precomputations complete".

### 6. Start the API Server
Start the FastAPI backend:
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```
*(Leave this terminal window running)*

---

## Confirming the System is Alive

With the server running, open a **new terminal** (or use your browser) to verify everything is working.

### Confirm Models are Trained and Loaded
Check the model performance and health endpoint:
```bash
curl http://localhost:8000/api/v1/models/performance
```
*Expected Output:* You should see a JSON response containing metrics for `tft` (val_wrmsse), `lightgbm` (pr_auc), and `lstm_ae` (current_threshold). This proves the pre-trained models are successfully loaded into memory.

### Confirm Database Seeding
Let's ask the system for the risk predictions it just made:
```bash
curl "http://localhost:8000/api/v1/suppliers?limit=10"
```
*Expected Output:* You should see JSON containing `DEMO-SUP-001` with a `risk_level` of `CRITICAL` or `HIGH` and a risk score > 0.85.

---

## Troubleshooting Common Setup Failures

| Issue | Expected Error Message | How to Fix |
| :--- | :--- | :--- |
| **Missing .env File** | `pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings` | You forgot to run `copy .env.example .env`. The app cannot start without this file. |
| **Port Conflict** | `[Errno 98] Address already in use` or `[WinError 10048]` | Another app is using port 8000. Stop it, or run uvicorn on a different port: `uvicorn api.main:app --port 8080` |
| **Database Connection Failure** | `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: action_logs` | You forgot to run `alembic upgrade head`. The database file exists but has no tables. |
| **Models Not Found** | `FileNotFoundError: No such file or directory: 'models/lgbm/checkpoints/best.joblib'` | You are missing the pre-trained model files. Ensure you have downloaded the required models into the `/models/` directory or ran `python scripts/download_datasets.py` if configured. |
