import asyncio
import sys
from pathlib import Path
import pytest
from sqlalchemy import select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.models.db import async_session_factory
from api.models.db_models import (
    CachedSupplierRisk,
    CachedSkuDemand,
    ModelTrainingJob,
    InventoryLevel
)
from api.services.inventory_service import inventory_heatmap_service
from agent.orchestrator import get_compiled_app


@pytest.mark.asyncio
async def test_cached_supplier_risk_crud():
    async with async_session_factory() as db:
        # Test inserting CachedSupplierRisk
        risk = CachedSupplierRisk(
            supplier_id="SUP-TEST-99",
            risk_score=0.75,
            risk_level="HIGH",
            is_anomaly=True,
            shap_drivers_json=[{"feature": "prev_otd", "impact": 0.35, "direction": "increases_risk"}]
        )
        db.add(risk)
        await db.commit()

        # Query back
        stmt = select(CachedSupplierRisk).where(CachedSupplierRisk.supplier_id == "SUP-TEST-99")
        res = await db.execute(stmt)
        retrieved = res.scalar_one_or_none()
        
        assert retrieved is not None
        assert retrieved.risk_score == 0.75
        assert retrieved.risk_level == "HIGH"
        assert retrieved.is_anomaly is True
        assert retrieved.shap_drivers_json[0]["feature"] == "prev_otd"

        # Cleanup
        await db.delete(retrieved)
        await db.commit()


@pytest.mark.asyncio
async def test_inventory_levels_preseed_and_load():
    async with async_session_factory() as db:
        sku_id = "FOODS_1_001_CA_1_evaluation"
        
        # Query inventory levels; build_heatmap should pre-seed
        skus = await inventory_heatmap_service.build_heatmap(db)
        assert len(skus) > 0
        
        # Verify the SKU was persisted in the inventory_levels table
        stmt = select(InventoryLevel).where(InventoryLevel.sku_id == sku_id)
        res = await db.execute(stmt)
        inv = res.scalar_one_or_none()
        
        assert inv is not None
        assert inv.units_on_hand > 0


@pytest.mark.asyncio
async def test_retraining_job_logging():
    async with async_session_factory() as db:
        # Insert retraining job
        job = ModelTrainingJob(
            model_name="LightGBM",
            status="RUNNING",
            log_file="logs/test_job.log"
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        assert job.id is not None
        assert job.status == "RUNNING"

        # Cleanup
        await db.delete(job)
        await db.commit()


@pytest.mark.asyncio
async def test_langgraph_sqlite_compilation():
    app = get_compiled_app()
    assert app is not None
    # Verify it compiles with checkpointer configured
    assert app.checkpointer is not None


from fastapi.testclient import TestClient
from api.main import app as fastapi_app
from api.middleware.auth import create_jwt_token

def test_health_check_endpoint():
    fastapi_app.state.health_cache = {
        "status": "ok",
        "app": "SupplyMind",
        "version": "2.0.0",
        "redis_connected": True,
        "scheduler_running": True,
        "scheduler_jobs": []
    }
    client = TestClient(fastapi_app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "redis_connected" in data
    assert "scheduler_running" in data

def test_retrain_status_and_logs_endpoints():
    async def setup_db():
        async with async_session_factory() as db:
            job = ModelTrainingJob(
                model_name="LightGBM",
                status="RUNNING",
                log_file="logs/test_job_endpoint.log"
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)
            return job.id

    async def cleanup_db(job_id):
        async with async_session_factory() as db:
            db_job = await db.get(ModelTrainingJob, job_id)
            if db_job:
                await db.delete(db_job)
                await db.commit()

    import asyncio
    job_id = asyncio.run(setup_db())
        
    log_path = Path("logs/test_job_endpoint.log")
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("Hello from retrain log stream test!", encoding="utf-8")
        
        token = create_jwt_token("test_user", "admin")
        headers = {"Authorization": f"Bearer {token}"}
        
        client = TestClient(fastapi_app)
        response = client.get("/api/v1/models/retrain/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        jobs = [j for j in data["jobs"] if j["job_id"] == job_id]
        assert len(jobs) == 1
        assert jobs[0]["model_name"] == "LightGBM"
        assert jobs[0]["status"] == "RUNNING"
        
        response_filtered = client.get("/api/v1/models/retrain/status?model_name=LightGBM", headers=headers)
        assert response_filtered.status_code == 200
        data_filtered = response_filtered.json()
        assert all(j["model_name"] == "LightGBM" for j in data_filtered["jobs"])
        
        response_logs = client.get(f"/api/v1/models/retrain/{job_id}/logs", headers=headers)
        assert response_logs.status_code == 200
        assert response_logs.text == "Hello from retrain log stream test!"
        
        response_not_found = client.get("/api/v1/models/retrain/999999/logs", headers=headers)
        assert response_not_found.status_code == 404
            
    finally:
        asyncio.run(cleanup_db(job_id))
        if log_path.exists():
            log_path.unlink()
