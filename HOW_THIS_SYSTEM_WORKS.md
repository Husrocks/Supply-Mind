# How SupplyMind Works

Welcome to SupplyMind! This document explains how the system operates in plain language so that anyone reviewing the project can understand its mechanics, data sources, and automation boundaries.

## 1. What Data Exists and Where It Came From

SupplyMind relies on several datasets to understand demand (what customers want) and supply (how reliable the suppliers are).

### The Datasets
*   **M5 Demand Forecast Data:** Real historical retail sales data from Kaggle. This represents the daily sales history of our products (SKUs) and is used to predict future demand. This is a one-time training input.
*   **DataCo & USAID Supply Chain Data:** Historical shipping and delivery records from Kaggle. We use this to learn what factors cause late deliveries or defects. This is a one-time training input.
*   **Synthetic Supplier Data:** Because real supplier risk data is highly confidential, we generate simulated supplier performance histories (e.g., how often they deliver on time, their financial stress). This data is continuously "read" by the system as if it were a live feed of supplier metrics.
*   **FRED Economic Data:** Macro-economic indicators (like inflation or shipping indices) used to add real-world context to the models.

### Machine Learning Models
**The machine learning models were trained once on this historical data.** They do not retrain themselves automatically in the background. They use the patterns they learned during that initial training to make predictions on new data. If you want the models to learn from new patterns, a human must click the "Retrain Models" button.

### Current Database Scale
Right now, the system's database contains a simulated environment of **1,200 suppliers** and **200 SKUs**, with about 2 years of historical performance data. This gives the system enough scale to demonstrate complex supply chain logic without requiring a massive supercomputer.

---

## 2. What is Automatic vs. What Requires Human Input

SupplyMind acts as an "Agent" that can make decisions. However, it operates within strict boundaries.

### Fully Automatic Actions (No Human Needed)
*   **Tier 1 Actions (Autonomous):** If the system predicts a problem, and the cost to fix it (like ordering emergency stock) is under the $85,000 budget, AND the system is highly confident in its prediction, it will automatically execute the action. It will just send a notification telling you what it did.
*   **Risk Scoring:** The system continuously calculates risk scores and days-to-stockout behind the scenes without human prompting.

### Actions Requiring Human Input (Clicks)
*   **Tier 2 Actions (Recommend & Confirm):** If a proposed solution costs more than the $85,000 autonomous budget, or if the supplier is brand new (in their 90-day probationary period), the system will *not* act automatically. It will prepare an "Action Card" detailing the problem, its reasoning, and the recommended solution. A human must click **Approve** or **Reject**.
*   **Tier 3 Actions (Escalate):** If the system detects a massive cascade failure or is very uncertain about its prediction, it will simply gather the context and escalate the issue to a human manager to handle manually.

### Human Configuration Settings
A human manager can change the boundaries of the system at any time via the Settings UI or the `.env` configuration file:
*   **Autonomous Budget ($85k default):** Change the maximum dollar amount the agent is allowed to spend automatically.
*   **Risk Thresholds:** Change the threshold at which a supplier is considered "High" or "Critical" risk (e.g., 0.75 or 0.85).
*   **Warning Days:** Change how many days out a "Days-to-Stockout" warning should trigger (default is 14 days).

---

## 3. The Three Ways the Agent Gets Triggered

The SupplyMind agent doesn't just sit there waiting; it actively monitors the supply chain. It wakes up and evaluates the supply chain in three different ways:

1.  **The Scheduled Trigger (The Routine Check):** Every day at 3:00 AM UTC (configurable), the agent wakes up and performs a complete sweep of all SKUs and suppliers, looking for any slow-moving risks or upcoming stockouts.
2.  **The Threshold/Event Trigger (The Alarm):** The system continuously listens to live data feeds (like simulated ERP or WMS systems). If a specific event happens—for example, a supplier's on-time delivery rate suddenly drops by 15%, or a massive demand spike occurs—the agent immediately wakes up to evaluate that specific SKU/Supplier pair.
3.  **The Manual Trigger (The Human Request):** A human user can go into the dashboard, select a specific SKU and Supplier, and click the **"Run Agent"** button. This forces the agent to evaluate that specific scenario immediately, regardless of schedule or alarms.

---

## 4. Glossary of Terms

Here is a quick guide to the specialized terms you will see in the user interface:

*   **Risk Score:** A percentage (0% to 100%) indicating the probability that a specific supplier will cause a disruption or stockout in the near future.
*   **Confidence Score:** How certain the machine learning model is about its own prediction. A low confidence score usually forces the system to ask a human for help.
*   **SHAP Driver:** The specific underlying reason *why* the model gave a certain risk score. (e.g., "Risk is high because the SHAP Driver 'Lead Time Variance' has severely increased").
*   **Disruption Probability:** The exact mathematical likelihood that an order placed today will not arrive on time.
*   **Anomaly Flag:** A true/false warning indicating that a supplier's recent behavior is highly unusual compared to their historical patterns, even if it hasn't resulted in a late delivery yet.
*   **Days-to-Stockout:** The estimated number of days until a specific product (SKU) completely runs out of inventory, based on the current demand forecast.
*   **Tier 1 / 2 / 3:** The permission levels for the agent. Tier 1 means the agent acts automatically; Tier 2 means it recommends an action but needs human approval; Tier 3 means it gives up and asks a human to solve it.
*   **Autonomous Budget Authority:** The maximum amount of money (e.g., $85,000) the agent is allowed to spend without asking for human permission.
*   **Reconstruction Error:** A technical metric used by the Anomaly Detector. A higher error means the current situation looks very different from "normal" historical data.
*   **WRMSSE:** A complex accuracy metric (Weighted Root Mean Squared Scaled Error) used to grade how accurate the demand forecasting model is. Lower is better.
