"""
SupplyMind — Hugging Face Spaces Gradio + FastAPI Launcher
Allows running with sdk: gradio (ZeroGPU compatible) while exposing all FastAPI REST API routes.
"""

import os
import sqlite3
import logging

logger = logging.getLogger("app")

# 1. Ensure SQLite database is restored from seed.sql if absent
_base_dir = os.path.dirname(os.path.abspath(__file__))
_db_file = os.path.join(_base_dir, "supplymind.db")
_sql_file = os.path.join(_base_dir, "seed.sql")

if not os.path.exists(_db_file) and os.path.exists(_sql_file):
    print("Auto-initializing supplymind.db from seed.sql for Hugging Face...")
    try:
        con = sqlite3.connect(_db_file)
        with open(_sql_file, "r", encoding="utf-8") as f:
            con.executescript(f.read())
        con.close()
        print("Database auto-initialization complete.")
    except Exception as e:
        print(f"Warning: database initialization error: {e}")

# Explicitly force SQLite URL so asyncpg / postgres is never invoked on Hugging Face
_db_posix = _db_file.replace("\\", "/")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_posix}"
print(f"Hugging Face runtime using: {os.environ['DATABASE_URL']}")

# 2. Import existing FastAPI application
from api.main import app as fastapi_app

# 3. Mount Gradio interface
import gradio as gr

with gr.Blocks(title="SupplyMind AI Engine") as demo:
    gr.Markdown("# 🧠 SupplyMind — Supply Chain Risk & Decision Orchestration Engine")
    gr.Markdown(
        """
        ### 🟢 Backend API Services are Active (ZeroGPU Accelerated)
        This Space hosts the **Agentic AI & ML Backend** for SupplyMind with ZeroGPU capability.

        - 📖 **Interactive API Documentation (Swagger):** [/docs](/docs)
        - 🩺 **Health Check Endpoint:** [/health](/health)
        - ⚡ **API Base Path:** `/api/v1/`

        ---
        **Connected Frontend:**
        The React 19 Frontend Dashboard communicates with this Space via REST API endpoints.
        """
    )

# Mount Gradio app onto FastAPI root
app = gr.mount_gradio_app(fastapi_app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
