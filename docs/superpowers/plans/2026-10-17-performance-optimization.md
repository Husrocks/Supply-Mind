# SupplyMind Performance Optimization — Master Implementation Plan

**Goal:** Eliminate all identified performance bottlenecks so every page loads in under 3 seconds on localhost and the `/predictions/risk-context` endpoint responds in under 500ms on warm cache.

**Architecture:** Fix backend in strict dependency order — cache layer → data layer → async model offloading → route de-duplication → SQLite locks — then frontend proxy, query staggering, polling, fonts, and chart bundle splitting.

## Execution Checklist

- [ ] **Phase 0: Foundations**
  - [ ] Task 0.1: Fix the broken cache key generator in `api/services/cache.py` (exclude session/non-serializables)
  - [ ] Task 0.2: Switch Redis config in `.env` to localhost with fallback
- [ ] **Phase 1: Backend Data Layer**
  - [ ] Task 1.1: Pre-index supplier DataFrame & vectorise concentration ratios in `api/services/network_service.py`
  - [ ] Task 1.2: Batch InventoryLevel queries in `api/services/inventory_service.py` (eliminate N+1)
  - [ ] Task 1.3: Skip session commit on read-only requests in `api/models/db.py`
- [ ] **Phase 2: Async Model Offloading**
  - [ ] Task 2.1: Create `api/services/thread_pool.py` and wrap ML/SHAP inference in `run_in_thread`
- [ ] **Phase 3: Route De-Duplication**
  - [ ] Task 3.1: Direct DB lookup in single supplier (`api/routes/suppliers.py`) & SKU detail (`api/routes/inventory.py`)
  - [ ] Task 3.2: Direct DB lookup for report CSV generation (`api/routes/reports.py`)
- [ ] **Phase 4: Dev Server Watcher**
  - [ ] Task 4.1: Create `scripts/dev_server.ps1` & `scripts/dev_server.sh` with scoped reload dirs
- [ ] **Phase 5: Frontend Performance**
  - [ ] Task 5.1: Add Vite dev proxy in `frontend-v2/vite.config.ts` (eliminate CORS OPTIONS preflight)
  - [ ] Task 5.2: Stagger dashboard queries in `frontend-v2/src/hooks/useDashboardQueries.ts`
  - [ ] Task 5.3: Reduce dev-mode polling frequency
  - [ ] Task 5.4: Make Google Fonts non-blocking in `frontend-v2/index.html` & `src/index.css`
  - [ ] Task 5.5: Lazy-load ForceGraph2D in `frontend-v2/src/views/NetworkDashboard.tsx`
- [ ] **Phase 6: Verification**
  - [ ] Task 6.1: Run tests and benchmarks
  - [ ] Task 6.2: Create `PERF.md` log
