"""
SupplyMind — Inventory Heatmap Service
Builds SKU inventory risk rows from real demand parquet data.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from agent.orchestrator import get_orchestrator

logger = logging.getLogger(__name__)

MAX_SKUS = 12


class InventoryHeatmapService:
    async def build_heatmap(self, db: AsyncSession) -> list[dict]:
        demand_df = get_orchestrator()._load_demand_data()
        if demand_df.empty:
            return []

        sku_ids = demand_df["id"].unique()[:MAX_SKUS].tolist()
        results: list[dict] = []

        from api.models.db_models import InventoryLevel
        from sqlalchemy import select

        for sku_id in sku_ids:
            rows = demand_df[demand_df["id"] == sku_id].sort_values("d")
            if rows.empty or "sales" not in rows.columns:
                continue

            recent = rows.tail(28)
            daily_avg = float(recent["sales"].mean())

            # Query the database for the real inventory level
            stmt = select(InventoryLevel).where(InventoryLevel.sku_id == sku_id)
            db_res = await db.execute(stmt)
            inv_level = db_res.scalar_one_or_none()

            if inv_level is not None:
                current_inventory = float(inv_level.units_on_hand)
            else:
                # Pre-seed database on first load with fallback proxy value
                current_inventory = float(recent.tail(14)["sales"].sum())
                inv_level = InventoryLevel(
                    sku_id=sku_id,
                    units_on_hand=int(current_inventory),
                    units_in_transit=int(current_inventory * 0.3),
                    reorder_point=1000
                )
                db.add(inv_level)
                await db.commit()

            days_to_stockout = current_inventory / max(daily_avg, 0.01)

            if "rolling_std_7" in recent.columns and pd.notna(recent["rolling_std_7"].iloc[-1]):
                uncertainty = float(recent["rolling_std_7"].iloc[-1]) * 14
            else:
                uncertainty = float(recent["sales"].std() or 0) * 14

            history = self._build_history(rows)
            status = (
                "CRITICAL"
                if days_to_stockout < 14
                else ("ELEVATED" if days_to_stockout < 21 else "NORMAL")
            )

            results.append({
                "sku_id": sku_id,
                "days_to_stockout": round(days_to_stockout, 1),
                "uncertainty_spread": round(uncertainty, 1),
                "current_inventory": round(current_inventory, 0),
                "status": status,
                "forecast_history": history,
            })

        return results

    def _build_history(self, rows: pd.DataFrame) -> list[dict]:
        history: list[dict] = []
        tail = rows.tail(28)
        recent_avg = float(tail["sales"].mean()) if not tail.empty else 0.0
        std = float(tail["sales"].std() or 0.0)

        for _, row in tail.iterrows():
            date_val = row.get("date")
            if pd.isna(date_val):
                date_str = str(int(row["d"]))
            elif hasattr(date_val, "strftime"):
                date_str = date_val.strftime("%Y-%m-%d")
            else:
                date_str = str(date_val)[:10]

            sales = float(row["sales"])
            history.append({
                "date": date_str,
                "actual": int(sales),
                "p50": None,
                "p05": None,
                "p95": None,
            })

        last_date = datetime.now()
        if "date" in tail.columns and pd.notna(tail["date"].iloc[-1]):
            try:
                last_date = pd.to_datetime(tail["date"].iloc[-1]).to_pydatetime()
            except Exception:
                pass

        for i in range(1, 15):
            date_str = (last_date + timedelta(days=i)).strftime("%Y-%m-%d")
            p50 = int(recent_avg * (1 + 0.02 * i))
            spread = int(std * (1 + 0.1 * i))
            history.append({
                "date": date_str,
                "actual": None,
                "p50": p50,
                "p05": max(0, p50 - spread),
                "p95": p50 + spread,
            })

        return history


inventory_heatmap_service = InventoryHeatmapService()
