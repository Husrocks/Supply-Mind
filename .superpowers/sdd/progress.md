# Performance Optimization Progress Ledger

- [x] Task 0.1: Fix broken cache key generator in `api/services/cache.py` (commit f38117f)
- [x] Task 0.2: Switch local Redis config to localhost (commits 3691b40, 49859d4)
- [x] Task 1.1: Pre-index supplier DataFrame & vectorise concentration in `api/services/network_service.py` (commit 892c7e7)
- [x] Task 1.2: Batch InventoryLevel queries in `api/services/inventory_service.py` (commit 4aae1c0)
- [x] Task 1.3: Skip session commit on read-only requests in `api/models/db.py` (commit 415c817)
- [x] Task 2.1: Offload ML & SHAP inference to thread pool via `api/services/thread_pool.py` (commit 8082ef0)
- [ ] Task 3.1: Direct DB lookup in single supplier & SKU detail endpoints
- [ ] Task 3.2: Direct DB lookup for report CSV generation
- [ ] Task 4.1: Scoped Uvicorn dev server scripts
- [ ] Task 5.1: Configure Vite dev proxy for `/api` and `/health`
- [ ] Task 5.2: Stagger dashboard queries in `useDashboardQueries.ts`
- [ ] Task 5.3: Reduce dev polling frequency
- [ ] Task 5.4: Non-blocking Google Fonts
- [ ] Task 5.5: Lazy-load ForceGraph2D
- [ ] Task 6.1: Full stack test & benchmark verification
- [ ] Task 6.2: Create `PERF.md` log
