import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path
import os

def seed_demo_scenario():
    print("Seeding DEMO scenario into processed datasets and database...")
    
    # 1. Supplier Data
    sup_path = Path("data/processed/supplier_train.parquet")
    if sup_path.exists():
        df_sup = pd.read_parquet(sup_path)
        demo_suppliers = []
        countries = [
            "USA", "China", "Germany", "Taiwan", "Mexico", "Vietnam", "India", 
            "Canada", "Japan", "Brazil", "South Korea", "UK", "France", 
            "Italy", "Australia", "Malaysia", "Singapore", "Thailand", 
            "Netherlands", "Spain"
        ]
        
        for i in range(1, 101):
            demo_sup = df_sup.iloc[-1].copy()
            
            # Ensure the specific IDs referenced in the docs exist
            if i == 1:
                sup_id = "DEMO-SUP-001"
            elif i == 2:
                sup_id = "DEMO-SUP-ALT"
            else:
                sup_id = f"DEMO-SUP-{i:03d}"
                
            demo_sup["supplier_id"] = sup_id
            
            # Deterministically create diverse risk profiles
            risk_profile = i % 4
            if risk_profile == 0:
                # Critical
                otd = 0.5 + (i * 0.005)
                lt = 100.0 + (i * 1.5)
                fs = 0.8 + (i * 0.005)
                pa = 0.4 + (i * 0.01)
                tier = "Tier 2"
                disrupted = 1
            elif risk_profile == 1:
                # Elevated
                otd = 0.7 + (i * 0.005)
                lt = 60.0 + (i * 1.0)
                fs = 0.6 + (i * 0.01)
                pa = 0.7 + (i * 0.01)
                tier = "Tier 2"
                disrupted = 1
            elif risk_profile == 2:
                # Normal
                otd = 0.85 + (i * 0.002)
                lt = 30.0 + (i * 0.5)
                fs = 0.3 + (i * 0.01)
                pa = 0.85 + (i * 0.005)
                tier = "Tier 1"
                disrupted = 0
            else:
                # Excellent
                otd = 0.95 + (i * 0.001)
                lt = 14.0 + (i * 0.2)
                fs = 0.1 + (i * 0.005)
                pa = 0.98 + (i * 0.001)
                tier = "Tier 1"
                disrupted = 0
                
            # Overrides for the two specifically required by docs
            if sup_id == "DEMO-SUP-001":
                otd, lt, fs, pa, tier, disrupted = 0.58, 120.0, 0.95, 0.40, "Tier 2", 1
            elif sup_id == "DEMO-SUP-ALT":
                otd, lt, fs, pa, tier, disrupted = 0.99, 14.0, 0.05, 0.99, "Tier 1", 0
                
            if "otd_mean_4w" in demo_sup: demo_sup["otd_mean_4w"] = otd
            if "prev_otd" in demo_sup: demo_sup["prev_otd"] = otd
            if "lead_time_mean_4w" in demo_sup: demo_sup["lead_time_mean_4w"] = lt
            if "prev_lead_time" in demo_sup: demo_sup["prev_lead_time"] = lt
            if "financial_stress_score" in demo_sup: demo_sup["financial_stress_score"] = fs
            if "po_accept_mean_4w" in demo_sup: demo_sup["po_accept_mean_4w"] = pa
            if "prev_po_accept" in demo_sup: demo_sup["prev_po_accept"] = pa
            if "contract_tier" in demo_sup: demo_sup["contract_tier"] = tier
            if "disrupted" in demo_sup: demo_sup["disrupted"] = disrupted
            
            # Add diverse geographic and quality attributes
            country = countries[i % len(countries)]
            if "country" in demo_sup: demo_sup["country"] = country
            if "regional_delay_factor" in demo_sup: demo_sup["regional_delay_factor"] = (i % 5) * 0.15
            if "defect_rate" in demo_sup: demo_sup["defect_rate"] = 0.01 * (i % 8)
            if "defect_rate_pct" in demo_sup: demo_sup["defect_rate_pct"] = 0.01 * (i % 8)
            
            demo_suppliers.append(demo_sup)
        
        df_sup = pd.concat([df_sup, pd.DataFrame(demo_suppliers)], ignore_index=True)
        df_sup.to_parquet(sup_path, index=False)
        print(f"Added {len(demo_suppliers)} diverse DEMO suppliers to {sup_path}")

    # 2. Demand Data
    dem_path = Path("data/processed/demand_features.parquet")
    if dem_path.exists():
        df_dem = pd.read_parquet(dem_path)
        # Create a SKU that is selling fast
        base_sku_id = df_dem["id"].iloc[0]
        demo_sku = df_dem[df_dem["id"] == base_sku_id].copy()
        demo_sku["id"] = "DEMO-SKU-001"
        if "item_id" in demo_sku: demo_sku["item_id"] = "DEMO-SKU-001"
        # Make demand very high so it stocks out quickly
        if "sales" in demo_sku: demo_sku["sales"] = 800
        if "rolling_mean_7" in demo_sku: demo_sku["rolling_mean_7"] = 800
        if "rolling_mean_28" in demo_sku: demo_sku["rolling_mean_28"] = 800
        if "sell_price" in demo_sku: demo_sku["sell_price"] = 120.0 # Make sure cost exceeds 85k threshold (800 * 14 * 120 = ~1.3M)
        
        df_dem = pd.concat([df_dem, demo_sku], ignore_index=True)
        df_dem.to_parquet(dem_path, index=False)
        print(f"Added DEMO-SKU-001 to {dem_path}")

    # 3. Database Updates
    db_path = Path("supplymind.db")
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Insert or update inventory level to be critically low
        cursor.execute('''
            INSERT INTO inventory_levels (sku_id, units_on_hand, units_in_transit, reorder_point, updated_at)
            VALUES ('DEMO-SKU-001', 1500, 0, 5000, CURRENT_TIMESTAMP)
            ON CONFLICT(sku_id) DO UPDATE SET units_on_hand=1500, reorder_point=5000;
        ''')

        # Insert seeded risk scores into cached_supplier_risks
        import json
        for i, sup in enumerate(demo_suppliers):
            sid = sup["supplier_id"]
            risk_profile = (i + 1) % 4
            
            if sid == "DEMO-SUP-001" or risk_profile == 0:
                score, level = 0.92, "CRITICAL"
                is_anom = 1
            elif risk_profile == 1:
                score, level = 0.75, "HIGH"
                is_anom = 1
            elif risk_profile == 2:
                score, level = 0.55, "ELEVATED"
                is_anom = 0
            else:
                score, level = 0.15, "NORMAL"
                is_anom = 0
                
            if sid == "DEMO-SUP-ALT":
                score, level = 0.05, "NORMAL"
                is_anom = 0
                
            drivers = json.dumps([
                {"feature": "lead_time_mean_4w", "value": sup.get("lead_time_mean_4w", 50), "impact": 1.2, "direction": "increases_risk"},
                {"feature": "prev_otd", "value": sup.get("prev_otd", 0.5), "impact": 0.8, "direction": "increases_risk"}
            ])
            
            cursor.execute('''
                INSERT INTO cached_supplier_risks (supplier_id, risk_score, risk_level, is_anomaly, shap_drivers_json, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(supplier_id) DO UPDATE SET 
                    risk_score=excluded.risk_score, 
                    risk_level=excluded.risk_level, 
                    is_anomaly=excluded.is_anomaly, 
                    shap_drivers_json=excluded.shap_drivers_json, 
                    updated_at=CURRENT_TIMESTAMP;
            ''', (sid, score, level, is_anom, drivers))
        
        conn.commit()
        conn.close()
        print("Updated SQLite database inventory levels and cached risks.")
    else:
        print("supplymind.db not found, skipping DB updates.")

    print("\nDemo scenario seeded successfully!")
    print("Run: curl -X POST http://localhost:8000/api/v1/agent/trigger -H 'Content-Type: application/json' -d '{\"sku_id\":\"DEMO-SKU-001\", \"primary_supplier_id\":\"DEMO-SUP-001\", \"alternative_supplier_ids\":[\"DEMO-SUP-ALT\"]}'")

if __name__ == "__main__":
    seed_demo_scenario()
