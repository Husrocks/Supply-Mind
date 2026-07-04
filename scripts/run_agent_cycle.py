#!/usr/bin/env python
"""
SupplyMind — End-to-End Agent Cycle Demonstration (Phase 5)

Usage:
    python scripts/run_agent_cycle.py
    python scripts/run_agent_cycle.py --sku FOODS_1_001_CA_1 --supplier SUP001

This script:
  1. Loads real processed parquets from data/processed/
  2. Picks a real SKU and supplier from the data (or uses provided args)
  3. Runs a complete OODA cycle
  4. Prints a rich, structured summary of the RiskContextFrame + ActionPlan
  5. Writes the cycle to logs/agent_audit.jsonl
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# ── Make sure repo root is on path ────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_agent_cycle")

# ── Separator helpers ─────────────────────────────────────────────────────────
SEP = "=" * 70
SEP2 = "-" * 70

TIER_EMOJI = {
    "AUTONOMOUS": "[AUTO]",
    "RECOMMEND_CONFIRM": "[HUMAN]",
    "ESCALATE": "[ALERT]",
}

RISK_EMOJI = {
    "NORMAL": "[OK]",
    "ELEVATED": "[WARN]",
    "HIGH": "[HIGH]",
    "CRITICAL": "[CRIT]",
    "UNKNOWN": "[?]",
}


def print_header(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(f"{SEP}")


def print_section(title: str) -> None:
    print(f"\n{SEP2}")
    print(f"  {title}")
    print(f"{SEP2}")


def print_context_frame(context: dict) -> None:
    """Pretty-print the RiskContextFrame."""
    print_header("RISK CONTEXT FRAME")

    sku = context.get("sku_id", "N/A")
    crit = context.get("criticality", "N/A")
    overall = context.get("overall_risk_level", "N/A")
    inventory = context.get("current_inventory", 0)

    print(f"  SKU:         {sku}")
    print(f"  Criticality: {'** TIER 1 - CRITICAL **' if crit == 'TIER_1' else 'TIER 2 - NORMAL'}")
    print(f"  Overall Risk: {RISK_EMOJI.get(overall, '[?]')} {overall}")
    print(f"  Inventory:   {inventory:,} units")

    # Demand
    demand = context.get("demand", {})
    print_section("DEMAND FORECAST (14-day horizon)")
    print(f"  P05 demand:  {demand.get('p05_14day_total', 0):.0f} units")
    print(f"  P50 demand:  {demand.get('p50_14day_total', 0):.0f} units")
    print(f"  P95 demand:  {demand.get('p95_14day_total', 0):.0f} units")
    print(f"  Uncertainty: {demand.get('demand_uncertainty_pct', 0):.0%}")
    dts50 = demand.get("days_to_stockout_p50")
    dts95 = demand.get("days_to_stockout_p95")
    print(f"  Stockout P50: {'[WARN] ' + f'{dts50:.1f} days' if dts50 else '[OK] > 14 days'}")
    print(f"  Stockout P95: {'[WARN] ' + f'{dts95:.1f} days' if dts95 else '[OK] > 14 days'}")

    # Primary Supplier
    primary = context.get("primary_supplier", {})
    rl = primary.get("risk_level", "UNKNOWN")
    print_section(f"PRIMARY SUPPLIER: {primary.get('supplier_id', 'N/A')}")
    print(f"  Risk Score:   {primary.get('risk_score', 0):.1%}")
    print(f"  Risk Level:   {RISK_EMOJI.get(rl, '[?]')} {rl}")
    print(f"  Anomaly:      {'[ALERT] YES - LSTM-AE flagged unusual pattern' if primary.get('is_anomaly') else '[OK] None'}")
    if primary.get("is_anomaly"):
        print(f"  Recon Error:  {primary.get('reconstruction_error', 0):.2f}")
    print(f"  Avg Lead Time: {primary.get('avg_lead_time_days', 30):.0f} days")
    print(f"  On-Time Del.:  {primary.get('on_time_delivery_pct', 0):.0%}")
    print(f"  PO Accept.:    {primary.get('po_acceptance_rate', 0):.0%}")
    slope = primary.get("lead_time_slope_6w", 0)
    print(f"  Lead Time Trend: {'^ Worsening' if slope > 0 else 'v Improving'} ({slope:+.3f}/week)")

    # SHAP drivers
    drivers = primary.get("shap_drivers", [])
    if drivers:
        print(f"\n  Top SHAP Drivers:")
        for i, d in enumerate(drivers[:3], 1):
            arrow = "^" if d.get("direction") == "increases_risk" else "v"
            print(
                f"    {i}. {arrow} {d.get('feature', '?'):30s} "
                f"impact={d.get('impact', 0):+.4f}  "
                f"value={d.get('value', 0):.4f}"
            )

    # Alternatives
    alts = context.get("alternative_suppliers", [])
    if alts:
        print_section(f"ALTERNATIVE SUPPLIERS ({len(alts)})")
        for alt in alts:
            rl2 = alt.get("risk_level", "UNKNOWN")
            print(
                f"  {RISK_EMOJI.get(rl2, '[?]')} {alt.get('supplier_id', '?'):20s} "
                f"Risk: {rl2:10s} ({alt.get('risk_score', 0):.0%})  "
                f"Anomaly: {'YES' if alt.get('is_anomaly') else 'No'}"
            )


def print_action_plan(plan: dict) -> None:
    """Pretty-print the ActionPlan."""
    print_header("ACTION PLAN")

    reasoning = plan.get("reasoning_steps", [])
    if reasoning:
        print("  Reasoning Chain:")
        for i, step in enumerate(reasoning, 1):
            print(f"    {i}. {step}")

    actions = plan.get("actions", [])
    print(f"\n  Total Actions: {len(actions)}")
    print(f"  Total Est. Cost: ${plan.get('total_estimated_cost_usd', 0):,.2f}")

    for i, action in enumerate(actions, 1):
        tier = action.get("tier", "?")
        tag = TIER_EMOJI.get(tier, "?")
        print(f"\n  [{i}] {tag} {action.get('action_type', '?')}  [{tier}]")
        print(f"      SKU: {action.get('sku_id', '?')}")
        print(f"      Supplier: {action.get('supplier_id', '?')}")
        if action.get("estimated_cost_usd", 0) > 0:
            print(f"      Cost: ${action.get('estimated_cost_usd', 0):,.2f}")
        print(f"      Reasoning: {action.get('reasoning', '')}")


def print_dispatch_results(results: list[dict]) -> None:
    """Pretty-print dispatch outcomes."""
    print_header("DISPATCH RESULTS")

    status_tag = {
        "EXECUTED": "[DONE]",
        "PENDING_APPROVAL": "[PENDING]",
        "ESCALATED": "[ESCALATED]",
        "UNKNOWN_TIER": "[?]",
    }

    for r in results:
        st = r.get("status", "?")
        tag = status_tag.get(st, "[?]")
        print(f"  {tag} {r.get('action_type', '?')} -> {r.get('message', '')}")



def main():
    parser = argparse.ArgumentParser(
        description="Run a full SupplyMind OODA cycle end-to-end."
    )
    parser.add_argument("--sku", type=str, default=None, help="SKU ID to evaluate")
    parser.add_argument("--supplier", type=str, default=None, help="Primary supplier ID")
    parser.add_argument("--inventory", type=int, default=5000, help="Current inventory units")
    parser.add_argument("--alts", nargs="*", default=None, help="Alternative supplier IDs")
    args = parser.parse_args()

    print(f"\n{'*' * 70}")
    print("  SupplyMind - Agentic Supply Risk Manager")
    print("  Phase 5: End-to-End Risk Context Frame Demonstration")
    print(f"{'*' * 70}")

    # Import here so we only load models once we're in the right directory
    from agent.orchestrator import get_orchestrator

    orchestrator = get_orchestrator()

    # Auto-discover IDs from real data if not provided
    sku_id = args.sku
    supplier_id = args.supplier

    if not sku_id:
        available_skus = orchestrator.get_available_sku_ids(5)
        if not available_skus:
            print("\n[ERROR] No demand data found. Please place demand_features.parquet in data/processed/")
            sys.exit(1)
        sku_id = available_skus[0]
        print(f"\n  Auto-selected SKU: {sku_id}")
        print(f"  (Available: {available_skus})")

    if not supplier_id:
        available_suppliers = orchestrator.get_available_supplier_ids(10)
        if not available_suppliers:
            print("\n[ERROR] No supplier data found. Please place supplier_train.parquet in data/processed/")
            sys.exit(1)
        supplier_id = available_suppliers[0]
        alt_ids = available_suppliers[1:4] if len(available_suppliers) > 1 else None
        print(f"\n  Auto-selected Supplier: {supplier_id}")
        if alt_ids:
            print(f"  Auto-selected Alternatives: {alt_ids}")
    else:
        alt_ids = args.alts

    print(f"\n  Running OODA cycle for:")
    print(f"    SKU:         {sku_id}")
    print(f"    Primary Sup: {supplier_id}")
    print(f"    Inventory:   {args.inventory:,} units")
    print(f"    Alternatives: {alt_ids or 'none'}")
    print()

    # ── Run the cycle ──────────────────────────────────────────────────────
    result = orchestrator.run_cycle(
        sku_id=sku_id,
        primary_supplier_id=supplier_id,
        current_inventory=args.inventory,
        alternative_supplier_ids=alt_ids,
        trigger_type="DEMO",
    )

    if result.get("status") == "ERROR":
        print(f"\n[ERROR] OODA Cycle failed: {result.get('error_message')}")
        sys.exit(1)

    # ── Print results ──────────────────────────────────────────────────────
    print_context_frame(result["context"])
    print_action_plan(result["plan"])
    print_dispatch_results(result["dispatch_results"])

    # ── Audit log stats ────────────────────────────────────────────────────
    print_header("AUDIT LOG STATISTICS")
    stats = orchestrator.audit_stats
    print(f"  Total cycles:   {stats.get('total_cycles', 0)}")
    print(f"  Success rate:   {stats.get('success_rate_pct', 0):.1f}%")
    print(f"  Avg risk score: {stats.get('avg_risk_score', 0):.3f}")
    breakdown = stats.get("tier_breakdown", {})
    if breakdown:
        print(f"  Action tiers:   {json.dumps(breakdown)}")
    print(f"\n  Audit log: logs/agent_audit.jsonl")

    print(f"\n{'*' * 70}")
    print("  SupplyMind OODA cycle complete. SUCCESS")
    print(f"{'*' * 70}\n")


if __name__ == "__main__":
    main()
