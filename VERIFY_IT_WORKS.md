# Verify SupplyMind Works: A Guided Demo

This checklist walks you through a guaranteed, repeatable demonstration of SupplyMind's core capability: **predicting a high-risk supply chain failure and autonomously recommending a mitigation strategy that requires human budget approval (Tier 2).**

Please ensure you have completed all steps in `HOW_TO_RUN.md` before starting this checklist.

---

### Step 1: Trigger the Agent on the Demo Scenario
**Action:** Open a new terminal window and run the following command to manually trigger the agent to evaluate our seeded high-risk scenario:
```bash
curl -X POST http://localhost:8000/api/v1/agent/trigger \
  -H "Content-Type: application/json" \
  -d '{
        "sku_id": "DEMO-SKU-001", 
        "primary_supplier_id": "DEMO-SUP-001", 
        "alternative_supplier_ids": ["DEMO-SUP-ALT"]
      }'
```

**Expected Result:** The command will take a few seconds to run (as it executes the LangGraph OODA loop), and will return a large JSON response.
*   Look for `"status": "PENDING_HUMAN"`.
*   Look for `"human_approval_needed": true`.
*   Look for `"tier": "RECOMMEND_CONFIRM"`.
*   Take note of the `"thread_id"` returned in the JSON (it will likely be `"DEMO-SKU-001_DEMO-SUP-001"`).

---

### Step 2: Verify the AI's Reasoning Context
**Action:** We want to see *why* the agent decided this was a problem. In the JSON response from Step 1, look at the `"context"` block.

**Expected Result:** 
*   Under `"demand"`, you will see a massive 14-day total demand, and `"days_to_stockout_p95"` will show a critical warning (under 7 days).
*   Under `"primary_supplier"`, you will see `"risk_level": "CRITICAL"`, caused by the horrible on-time delivery rate (0.58) and high financial stress (0.95) that we deliberately seeded.
*   Under `"overall_risk_level"`, it will read `"CRITICAL"`.

---

### Step 3: Verify the Proposed Mitigation Plan
**Action:** Now, look at the `"plan"` block in the JSON response from Step 1.

**Expected Result:**
*   You will see an action in the `"actions"` list (likely an `"EMERGENCY_PO"` or `"SHIFT_SUPPLIER"`).
*   The `"estimated_cost_usd"` will be very high (likely over $100,000 due to the high demand and unit price we seeded).
*   Because this cost exceeds the system's `$85,000` autonomous budget, the `"tier"` for this action is `"RECOMMEND_CONFIRM"`.
*   The `"system_reasoning_summary"` will explicitly state that a human must approve this action due to the budget limit being exceeded.

---

### Step 4: Verify the Action is Pending in the Database
**Action:** Let's confirm this action is actually waiting for a manager in the database. Run this command:
```bash
curl http://localhost:8000/api/v1/agent/actions/pending
```

**Expected Result:** You will get a JSON list containing the action generated in Step 1. The `"status"` will be `"PENDING"`, the `"sku_id"` will be `"DEMO-SKU-001"`, and the `"trigger_type"` will be `"MANUAL"`. Note the `"action_plan_id"` or `"id"` for the next step.

---

### Step 5: Simulate the Human Manager Approving the Action
**Action:** SupplyMind's agent is currently paused, waiting for human input. We will now provide that approval to resume the agent's workflow. Run this command (replacing the `thread_id` if yours was different):
```bash
curl -X POST http://localhost:8000/api/v1/agent/resume \
  -H "Content-Type: application/json" \
  -d '{
        "thread_id": "DEMO-SKU-001_DEMO-SUP-001",
        "human_decision": "approved"
      }'
```

**Expected Result:** The system will confirm the action was approved and successfully executed. Behind the scenes, the autonomous agent wakes back up, receives your approval, and automatically fires off the emergency purchase order to the mock ERP system.

---

### Step 6: Verify the Final Audit Trail
**Action:** A core feature of SupplyMind is the permanent audit trail. Let's retrieve the final log of what just happened.
```bash
curl http://localhost:8000/api/v1/agent/audit
```

**Expected Result:** You will see a complete historical record of the event. It will show the initial ML predictions, the context that was built, the action plan that was decided upon, the fact that a human intervened to approve it, and the final `"SUCCESS"` execution status.

**Congratulations! You have verified the end-to-end predictive and autonomous orchestration capabilities of SupplyMind.**

---

### Step 7: Check the Scheduler Status Display
**Action:** The system doesn't just wait for manual triggers; it runs a background scheduler to continuously monitor the network. Let's check its status. Run this command:
```bash
curl http://localhost:8000/api/v1/scheduler/status
```

**Expected Result:** The system will return the current state of its background routine. You will see whether the scheduler is actively running, the exact time it last woke up to check for risks, and the next scheduled time it plans to run a sweep.

---

### Step 8: Verify the Geographic Map & Dashboard Charts Data
**Action:** SupplyMind's Command Center UI visualizes risk using Geographic Maps, Sankey diagrams, and Treemaps. Let's verify that the backend is properly serving our seeded `DEMO-SUP-001` data into the dashboard endpoint that powers these charts. Run this command:
```bash
curl http://localhost:8000/api/v1/predictions/risk-context
```

**Expected Result:** The system will output the full data package used to render the dashboard. 
*   **For the Geographic Map:** You will see `"country_code"` and `"geographic_risk_region"` populated for `DEMO-SUP-001`, which the UI uses to plot the supplier's risk on the globe.
*   **For the Sankey / Treemap:** You will see `"risk_score"` (which will be critically high) and `"geopolitical_factor"`. The UI uses these specific numeric weights to size the warning nodes in the Treemap and determine the thickness and color of the supply flows in the Sankey diagram.

---

### Alternative: Simulate the Reject Flow (with Justification Text)
**Action:** What if a manager disagrees with the agent's proposed action? The system requires justification to reject it. To simulate a manager rejecting an action because of a budget freeze, run this command (replace `1` with an actual pending action ID from Step 4):
```bash
curl -X POST http://localhost:8000/api/v1/agent/actions/1/reject \
  -H "Content-Type: application/json" \
  -d '{
        "rejected_by": "demo_manager",
        "reason": "Budget frozen. We cannot afford this right now."
      }'
```

**Expected Result:** The system will update the action's status to "REJECTED". It permanently records the manager's justification text ("Budget frozen...") into the audit trail, and the autonomous loop gracefully shuts down for this specific issue without spending any money.
