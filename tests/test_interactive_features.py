"""
Unit and Integration Tests for SupplyMind Real-World Interactive Features:
1. What-If Simulator
2. Smart Reorder Recommendations
3. Supplier Disruption Simulator
4. Explainable ML Predictions
5. Ask SupplyMind AI Assistant
6. Demo State Reset
"""

import pytest
from pathlib import Path
import sys
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.main import app
from api.models.db import async_session_factory
from api.middleware.auth import create_jwt_token
from api.schemas.interactive_schemas import (
    WhatIfRequest,
    DisruptionRequest,
    AssistantChatRequest,
)
from api.services.simulation_service import simulation_service
from api.services.reorder_service import reorder_service
from api.services.explainability_service import explainability_service
from api.services.assistant_service import assistant_service


@pytest.fixture
def auth_headers():
    token = create_jwt_token("test_admin", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_what_if_simulation_calculations():
    async with async_session_factory() as db:
        # 1. Baseline simulation (0% delta)
        req_base = WhatIfRequest(
            sku_id="FOODS_1_001_CA_1_evaluation",
            demand_change_pct=0.0,
            lead_time_increase_days=0,
        )
        res_base = await simulation_service.simulate_what_if(req_base, db)
        assert res_base.sku_id == "FOODS_1_001_CA_1_evaluation"
        assert res_base.baseline_daily_demand > 0
        assert res_base.delta_days_to_stockout == 0.0
        assert len(res_base.trajectory) == 31

        # 2. Demand surge simulation (+50% demand surge, +15 days lead time)
        req_shock = WhatIfRequest(
            sku_id="FOODS_1_001_CA_1_evaluation",
            demand_change_pct=50.0,
            lead_time_increase_days=15,
        )
        res_shock = await simulation_service.simulate_what_if(req_shock, db)
        assert res_shock.simulated_daily_demand > res_base.baseline_daily_demand
        assert res_shock.simulated_effective_lead_time_days == res_base.baseline_lead_time_days + 15
        assert res_shock.delta_days_to_stockout <= 0.0  # Runway reduced or equal
        assert len(res_shock.drivers) >= 2
        assert res_shock.simulated_risk_tier in ["CRITICAL", "ELEVATED", "NORMAL"]


@pytest.mark.asyncio
async def test_supplier_disruption_simulation():
    async with async_session_factory() as db:
        req = DisruptionRequest(
            supplier_id="SUP-0001",
            disruption_type="SHUTDOWN",
            duration_days=30,
            severity_pct=100.0,
        )
        res = await simulation_service.simulate_supplier_disruption(req, db)
        assert res.supplier_id == "SUP-0001"
        assert res.disrupted_risk_score > res.baseline_risk_score
        assert len(res.affected_skus) > 0
        assert len(res.recommended_mitigations) >= 2
        # Alternative candidates must not hallucinate unverified capacity
        if res.alternative_candidates:
            alt = res.alternative_candidates[0]
            assert alt.supplier_id != "SUP-0001"
            assert "capacity" in alt.capacity_status.lower() or "verified" in alt.capacity_status.lower()


@pytest.mark.asyncio
async def test_smart_reorder_recommendations_and_status():
    async with async_session_factory() as db:
        summary = await reorder_service.get_recommendations(db)
        assert summary.total_skus_evaluated > 0
        assert len(summary.recommendations) > 0
        
        first_rec = summary.recommendations[0]
        assert first_rec.reorder_point > 0
        assert first_rec.safety_stock > 0
        assert first_rec.days_to_stockout >= 0
        assert first_rec.criticality in ["CRITICAL", "ELEVATED", "NORMAL"]
        
        # Test status update
        update_res = await reorder_service.update_status(
            sku_id=first_rec.sku_id,
            status="REVIEWED",
            notes="Reviewed by supply chain test runner",
            updated_by="TestEngineer",
            db=db,
        )
        assert update_res["status"] == "REVIEWED"
        assert update_res["notes"] == "Reviewed by supply chain test runner"

        # Verify filter by status
        filtered = await reorder_service.get_recommendations(db, status_filter="REVIEWED")
        reviewed_skus = [r.sku_id for r in filtered.recommendations]
        assert first_rec.sku_id in reviewed_skus

        # Test CSV export
        csv_buf = await reorder_service.export_csv(db)
        csv_content = csv_buf.getvalue()
        assert "SupplyMind — Smart Reorder Recommendations Export" in csv_content
        assert "Reorder Point" in csv_content
        assert first_rec.sku_id in csv_content


@pytest.mark.asyncio
async def test_explainable_predictions_service():
    async with async_session_factory() as db:
        # Supplier explainability
        sup_exp = await explainability_service.get_supplier_explanation("SUP-0001", db)
        assert sup_exp.supplier_id == "SUP-0001"
        assert len(sup_exp.shap_drivers) > 0
        assert "ATTRIBUTION NOTICE" in sup_exp.attribution_disclaimer
        assert sup_exp.anomaly_threshold_mse == 50.0

        # SKU explainability
        sku_exp = await explainability_service.get_sku_explanation("FOODS_1_001_CA_1_evaluation", db)
        assert sku_exp.sku_id == "FOODS_1_001_CA_1_evaluation"
        assert sku_exp.p95_total_demand >= sku_exp.p50_total_demand >= sku_exp.p05_total_demand
        assert sku_exp.uncertainty_spread >= 0


@pytest.mark.asyncio
async def test_assistant_grounded_queries():
    async with async_session_factory() as db:
        # Query 1: High risk suppliers
        res_suppliers = await assistant_service.chat(
            AssistantChatRequest(question="Which suppliers currently have the highest risk?"),
            db=db,
        )
        assert res_suppliers.intent_detected == "high_risk_suppliers"
        assert len(res_suppliers.citations) > 0
        assert "supplier" in res_suppliers.answer.lower()

        # Query 2: Stockout risks
        res_stockouts = await assistant_service.chat(
            AssistantChatRequest(question="Which products may experience stockouts soon?"),
            db=db,
        )
        assert res_stockouts.intent_detected == "stockout_risk_skus"
        assert len(res_stockouts.citations) > 0

        # Query 3: What if query
        res_what_if = await assistant_service.chat(
            AssistantChatRequest(question="What happens if demand increases by 25%?"),
            db=db,
        )
        assert res_what_if.intent_detected == "what_if"
        assert "runway" in res_what_if.answer.lower()


@pytest.mark.asyncio
async def test_demo_reset():
    async with async_session_factory() as db:
        reset_res = await simulation_service.reset_demo_state(db)
        assert reset_res["status"] == "SUCCESS"


def test_api_endpoints_via_client(auth_headers):
    client = TestClient(app)

    # 1. What-If Endpoint
    res = client.post(
        "/api/v1/simulation/what-if",
        headers=auth_headers,
        json={"sku_id": "FOODS_1_001_CA_1_evaluation", "demand_change_pct": 10.0, "lead_time_increase_days": 5},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["sku_id"] == "FOODS_1_001_CA_1_evaluation"
    assert "trajectory" in data

    # 2. Supplier Disruption Endpoint
    res_disrupt = client.post(
        "/api/v1/simulation/supplier-disruption",
        headers=auth_headers,
        json={"supplier_id": "SUP-0001", "duration_days": 14, "severity_pct": 80.0},
    )
    assert res_disrupt.status_code == 200
    assert "affected_skus" in res_disrupt.json()

    # 3. Reorder Recommendations Endpoint
    res_reorder = client.get("/api/v1/reorder/recommendations", headers=auth_headers)
    assert res_reorder.status_code == 200
    assert "recommendations" in res_reorder.json()

    # 4. Reorder CSV Export
    res_csv = client.get("/api/v1/reorder/export", headers=auth_headers)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]

    # 5. Explainability Endpoints
    res_exp_sup = client.get("/api/v1/explainability/supplier/SUP-0001", headers=auth_headers)
    assert res_exp_sup.status_code == 200
    assert "shap_drivers" in res_exp_sup.json()

    res_exp_sku = client.get("/api/v1/explainability/sku/FOODS_1_001_CA_1_evaluation", headers=auth_headers)
    assert res_exp_sku.status_code == 200
    assert "p50_total_demand" in res_exp_sku.json()

    # 6. Assistant Endpoint
    res_chat = client.post(
        "/api/v1/assistant/chat",
        headers=auth_headers,
        json={"question": "Which suppliers currently have the highest risk?"},
    )
    assert res_chat.status_code == 200
    assert len(res_chat.json()["citations"]) > 0

    # 7. Reset Endpoint
    res_reset = client.post("/api/v1/simulation/reset", headers=auth_headers)
    assert res_reset.status_code == 200
