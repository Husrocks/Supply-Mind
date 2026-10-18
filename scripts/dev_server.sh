#!/usr/bin/env bash
# SupplyMind Scoped Backend Dev Server
# Scoped reload prevents SQLite WAL / DB file churn from triggering spurious full server restarts.
echo "Starting SupplyMind backend with scoped hot-reload (api, agent, models)..."
uvicorn api.main:app --reload --reload-dir api --reload-dir agent --reload-dir models --host 0.0.0.0 --port 8000
