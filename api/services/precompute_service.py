from __future__ import annotations

import logging
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.db_models import CachedSupplierRisk, CachedSkuDemand, InventoryLevel
from agent.orchestrator import get_orchestrator
from agent.context_builder import get_context_builder

logger = logging.getLogger(__name__)


async def run_precomputations(db: AsyncSession):
    """
    Observe/Predict for all suppliers and SKUs in background,
    and save predictions in the sqlite database.
    """
    logger.info("Starting prediction precomputations...")
    orchestrator = get_orchestrator()
    supplier_df = orchestrator._load_supplier_data()
    demand_df = orchestrator._load_demand_data()
    builder = get_context_builder()

    if supplier_df.empty or demand_df.empty:
        logger.error("Empty supplier or demand dataframes. Skipping precomputation.")
        return

    # 1. Pre-compute Supplier Risks & Anomalies
    supplier_ids = supplier_df["supplier_id"].unique().tolist()
    logger.info("Running risk predictions for %d suppliers...", len(supplier_ids))
    
    risk_map = builder._run_risk_predictions(supplier_ids, supplier_df)
    anomaly_map = builder._run_anomaly_detection(supplier_ids, supplier_df)
    
    for sid in supplier_ids:
        risk = risk_map.get(sid)
        anomaly = anomaly_map.get(sid)
        if not risk:
            continue
            
        is_anon = anomaly.is_anomaly if anomaly else False
        shap_drivers = []
        if hasattr(risk, "shap_drivers") and risk.shap_drivers:
            # risk is SupplierRiskPrediction model
            for d in risk.shap_drivers:
                # d is dict or ShapDriver
                if isinstance(d, dict):
                    shap_drivers.append(d)
                else:
                    shap_drivers.append(d.model_dump())
        elif isinstance(risk, dict):
            shap_drivers = risk.get("shap_drivers", [])
            
        stmt = select(CachedSupplierRisk).where(CachedSupplierRisk.supplier_id == sid)
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()
        
        score = risk.risk_score if hasattr(risk, "risk_score") else float(risk.get("risk_score", 0.0))
        level = risk.risk_level if hasattr(risk, "risk_level") else str(risk.get("risk_level", "UNKNOWN"))
        
        if record:
            record.risk_score = score
            record.risk_level = level
            record.is_anomaly = is_anon
            record.shap_drivers_json = shap_drivers
            record.updated_at = datetime.now(timezone.utc)
        else:
            record = CachedSupplierRisk(
                supplier_id=sid,
                risk_score=score,
                risk_level=level,
                is_anomaly=is_anon,
                shap_drivers_json=shap_drivers
            )
            db.add(record)
            
    await db.commit()
    logger.info("Supplier risk precomputations complete.")

    # 2. Pre-compute SKU Demand Forecasts
    sku_ids = demand_df["id"].unique()[:50].tolist()
    logger.info("Running demand forecasts for %d SKUs...", len(sku_ids))
    for sku_id in sku_ids:
        # Load inventory level or default to 5000
        stmt_inv = select(InventoryLevel).where(InventoryLevel.sku_id == sku_id)
        res_inv = await db.execute(stmt_inv)
        inv = res_inv.scalar_one_or_none()
        inv_units = inv.units_on_hand if inv else 5000
        
        try:
            signal = builder._run_demand_forecast(sku_id, demand_df, inv_units)
            stmt = select(CachedSkuDemand).where(CachedSkuDemand.sku_id == sku_id)
            res = await db.execute(stmt)
            record = res.scalar_one_or_none()
            
            daily_forecasts = signal.daily_forecasts if hasattr(signal, "daily_forecasts") else []
            
            p05 = signal.p05_14day_total if hasattr(signal, "p05_14day_total") else float(signal.get("p05_14day_total", 0.0))
            p50 = signal.p50_14day_total if hasattr(signal, "p50_14day_total") else float(signal.get("p50_14day_total", 0.0))
            p95 = signal.p95_14day_total if hasattr(signal, "p95_14day_total") else float(signal.get("p95_14day_total", 0.0))
            stockout = getattr(signal, "days_to_stockout_p50", None)
            
            if record:
                record.p05_total = p05
                record.p50_total = p50
                record.p95_total = p95
                record.days_to_stockout = stockout
                record.daily_forecasts_json = daily_forecasts
                record.updated_at = datetime.now(timezone.utc)
            else:
                record = CachedSkuDemand(
                    sku_id=sku_id,
                    p05_total=p05,
                    p50_total=p50,
                    p95_total=p95,
                    days_to_stockout=stockout,
                    daily_forecasts_json=daily_forecasts
                )
                db.add(record)
        except Exception as e:
            logger.error("Failed precomputation for SKU %s: %s", sku_id, e)
            
    await db.commit()
    logger.info("SKU demand precomputations complete.")
