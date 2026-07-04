# %% [markdown]
# # M5 Forecasting Dataset — Exploratory Data Analysis
# **Phase 1: Demand Signals**
# 
# This notebook explores the M5 Walmart dataset to understand demand patterns,
# missing values, product hierarchies, and prepare the dataset for the TFT model.

# %%
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Configure plotting
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("colorblind")
plt.rcParams['figure.figsize'] = (12, 6)

# Set raw data path
RAW_DATA_DIR = Path("data/raw/m5-forecasting-accuracy")

# %% [markdown]
# ## 1. Load Data
# The M5 dataset consists of three main files:
# 1. `calendar.csv`: Contains dates and events (holidays, SNAP).
# 2. `sell_prices.csv`: Contains price data per store and item.
# 3. `sales_train_evaluation.csv`: Contains daily sales data (1941 days).

# %%
def check_data_exists():
    if not RAW_DATA_DIR.exists() or not list(RAW_DATA_DIR.glob("*.csv")):
        print(f"WARNING: Data not found at {RAW_DATA_DIR}.")
        print("Run `python scripts/download_datasets.py` first.")
        return False
    return True

if check_data_exists():
    print("Loading datasets... This might take a minute.")
    calendar = pd.read_csv(RAW_DATA_DIR / "calendar.csv")
    sales = pd.read_csv(RAW_DATA_DIR / "sales_train_evaluation.csv")
    prices = pd.read_csv(RAW_DATA_DIR / "sell_prices.csv")
    print(f"Sales shape: {sales.shape} (Items x Days + Metadata)")
    print(f"Calendar shape: {calendar.shape}")
    print(f"Prices shape: {prices.shape}")

# %% [markdown]
# ## 2. Data Hierarchies & Metadata
# M5 is a hierarchical dataset: Item -> Category -> Department -> Store -> State.

# %%
if check_data_exists():
    print("Categories:", sales['cat_id'].unique())
    print("Departments:", sales['dept_id'].unique())
    print("States:", sales['state_id'].unique())
    print("Stores:", sales['store_id'].unique())
    
    # Let's count items per category
    item_counts = sales.groupby('cat_id')['item_id'].nunique()
    item_counts.plot(kind='bar', title='Number of Unique Items per Category')
    plt.show()

# %% [markdown]
# ## 3. Time Series Analysis (Aggregate Demand)
# Let's look at the overall demand across all stores and items over time.

# %%
if check_data_exists():
    # Extract just the day columns (d_1 to d_1941)
    d_cols = [c for c in sales.columns if c.startswith('d_')]
    
    # Sum daily sales across the entire dataset
    total_daily_sales = sales[d_cols].sum()
    
    # Convert index to actual dates using the calendar
    calendar_dates = calendar.set_index('d')['date'].to_dict()
    total_daily_sales.index = total_daily_sales.index.map(calendar_dates)
    total_daily_sales.index = pd.to_datetime(total_daily_sales.index)
    
    # Plot
    plt.figure(figsize=(15, 5))
    total_daily_sales.plot()
    plt.title("Total Daily Sales (All Items & Stores)")
    plt.ylabel("Units Sold")
    plt.xlabel("Date")
    plt.show()
    
    print("Notice the missing days (Christmas, when sales drop to exactly 0).")

# %% [markdown]
# ## 4. Sparsity and Zero-Sales Analysis
# Supply chain demand data is notoriously sparse. Let's quantify how many days have 0 sales.

# %%
if check_data_exists():
    zeros_pct = (sales[d_cols] == 0).sum().sum() / (sales[d_cols].shape[0] * sales[d_cols].shape[1]) * 100
    print(f"Percentage of exactly ZERO sales across all item-days: {zeros_pct:.2f}%")
    print("Conclusion: Intermittent demand forecasting requires models that handle sparse inputs well (like TFT).")

# %% [markdown]
# ## 5. Next Steps for Feature Engineering
# To feed this into the TFT model, we will need to:
# 1. Melt the dataset into a "long" format (Date, Item, Store, Sales).
# 2. Merge with Calendar to get events/SNAP indicators.
# 3. Merge with Prices.
# 4. Generate rolling features (7, 14, 28-day moving averages).
