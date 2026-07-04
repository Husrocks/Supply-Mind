# %% [markdown]
# # DataCo Smart Supply Chain Dataset — Exploratory Data Analysis
# **Phase 1: Supplier Risk Signals**
# 
# This notebook explores the DataCo dataset to understand logistics,
# delivery delays, shipping anomalies, and supplier risk features.

# %%
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("muted")

RAW_DATA_DIR = Path("data/raw/dataco-smart-supply-chain")

# %% [markdown]
# ## 1. Load Data
# The dataset contains order delivery statuses, customer info, and order routing details.

# %%
def check_data_exists():
    if not RAW_DATA_DIR.exists() or not list(RAW_DATA_DIR.glob("*.csv")):
        print(f"WARNING: Data not found at {RAW_DATA_DIR}.")
        print("Run `python scripts/download_datasets.py` first.")
        return False
    return True

if check_data_exists():
    print("Loading DataCo dataset...")
    # Find the main csv file
    csv_file = list(RAW_DATA_DIR.glob("*.csv"))[0]
    # Use latin1 encoding as DataCo often has encoding issues
    df = pd.read_csv(csv_file, encoding='latin1')
    print(f"Dataset shape: {df.shape}")
    print("\nColumns available:", list(df.columns))

# %% [markdown]
# ## 2. Delivery Status Analysis
# The target variable for logistics is understanding whether a delivery was late, on time, or cancelled.

# %%
if check_data_exists():
    status_counts = df['Delivery Status'].value_counts()
    
    plt.figure(figsize=(8, 5))
    sns.barplot(x=status_counts.values, y=status_counts.index)
    plt.title("Distribution of Delivery Statuses")
    plt.xlabel("Number of Orders")
    plt.show()
    
    late_pct = (status_counts.get("Late delivery", 0) / len(df)) * 100
    print(f"Late delivery rate: {late_pct:.2f}%")

# %% [markdown]
# ## 3. Lead Time Analysis (Scheduled vs. Actual)
# For our supplier disruption model, lead time variance is a critical feature.

# %%
if check_data_exists():
    plt.figure(figsize=(10, 5))
    
    # Scheduled vs actual days for shipping
    sns.kdeplot(df['Days for shipping (real)'], label="Actual Days", fill=True)
    sns.kdeplot(df['Days for shipment (scheduled)'], label="Scheduled Days", fill=True)
    
    plt.title("Scheduled vs. Actual Shipping Days")
    plt.xlabel("Days")
    plt.legend()
    plt.xlim(0, 10)
    plt.show()

# %% [markdown]
# ## 4. Feature Extraction for Synthetic Supplier Data
# We will use the statistics from this dataset to parameterize our
# `supplier_sim.py` synthetic data generator to ensure it acts like real-world data.

# %%
if check_data_exists():
    print("Key metrics to feed into our Synthetic Generator:")
    print("-" * 50)
    print(f"Mean Actual Shipping Days: {df['Days for shipping (real)'].mean():.2f}")
    print(f"StdDev Actual Shipping Days: {df['Days for shipping (real)'].std():.2f}")
    
    # Calculate defect/fraud rate as a proxy
    if "Order Status" in df.columns:
        suspected_fraud = (df['Order Status'] == 'SUSPECTED_FRAUD').sum() / len(df) * 100
        print(f"Proxy for Anomalies (Fraud Rate): {suspected_fraud:.2f}%")
