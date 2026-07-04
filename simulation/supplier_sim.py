"""
SupplyMind — Synthetic Supplier Data Generator
Phase 2 Foundation: Generates realistic supplier performance data.

This simulation models 1,200 suppliers over 104 weeks (2 years).
It enforces realistic correlations:
- Lead time variance increases before disruptions.
- PO acceptance rate drops during capacity crunches.
- 11% positive class imbalance for the disruption flag.
"""

import argparse
import numpy as np
import pandas as pd
from loguru import logger
import os

# Set reproducible seed
np.random.seed(42)

def generate_base_suppliers(num_suppliers: int) -> pd.DataFrame:
    """Generate static supplier metadata."""
    logger.info(f"Generating {num_suppliers} base supplier profiles...")
    
    supplier_ids = [f"SUP-{str(i).zfill(4)}" for i in range(1, num_suppliers + 1)]
    countries = np.random.choice(
        ["USA", "China", "Taiwan", "Germany", "Mexico", "Vietnam"], 
        size=num_suppliers, 
        p=[0.2, 0.35, 0.15, 0.1, 0.1, 0.1]
    )
    
    # Contract tiers with weights
    contract_tiers = np.random.choice(
        ["Tier 1", "Tier 2", "Tier 3"], 
        size=num_suppliers, 
        p=[0.1, 0.3, 0.6]
    )
    
    df = pd.DataFrame({
        "supplier_id": supplier_ids,
        "country": countries,
        "contract_tier": contract_tiers,
        "tenure_years": np.random.uniform(0.5, 10.0, size=num_suppliers).round(1)
    })
    
    return df

def generate_timeseries_data(suppliers_df: pd.DataFrame, num_weeks: int) -> pd.DataFrame:
    """Generate weekly performance metrics for each supplier."""
    logger.info(f"Generating time-series data for {num_weeks} weeks...")
    # NOTE: This is a skeleton. The full logic with correlated features, 
    # rolling averages, and disruption labels will be implemented in Phase 2.
    
    records = []
    
    # Simple mockup for the skeleton
    for _, supplier in suppliers_df.iterrows():
        base_lead_time = np.random.normal(14, 2)
        
        for week in range(1, num_weeks + 1):
            records.append({
                "supplier_id": supplier["supplier_id"],
                "week_num": week,
                "on_time_delivery_pct": np.clip(np.random.normal(0.92, 0.05), 0, 1),
                "po_acceptance_rate": np.clip(np.random.normal(0.95, 0.03), 0, 1),
                "avg_lead_time_days": max(1.0, np.random.normal(base_lead_time, 1.5)),
                "defect_rate_pct": max(0.0, np.random.normal(0.02, 0.01)),
                "disruption_flag": np.random.choice([0, 1], p=[0.89, 0.11])  # 11% imbalance
            })
            
    return pd.DataFrame(records)

def main(args):
    logger.info("Starting synthetic supplier data generation...")
    
    # 1. Generate static metadata
    suppliers_df = generate_base_suppliers(args.suppliers)
    
    # 2. Generate weekly time-series
    ts_df = generate_timeseries_data(suppliers_df, args.weeks)
    
    # 3. Merge
    final_df = ts_df.merge(suppliers_df, on="supplier_id", how="left")
    
    # 4. Save
    output_dir = "data/synthetic"
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "supplier_dataset.parquet")
    final_df.to_parquet(output_path, index=False)
    
    logger.info(f"Successfully generated {len(final_df)} records.")
    logger.info(f"Saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synthetic Supplier Data Generator")
    parser.add_argument("--suppliers", type=int, default=1200, help="Number of suppliers")
    parser.add_argument("--weeks", type=int, default=104, help="Number of weeks to simulate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    
    args = parser.parse_args()
    
    # Set seed globally
    np.random.seed(args.seed)
    
    main(args)
