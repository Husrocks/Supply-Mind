"""
SupplyMind — Agent Orchestrator (LangGraph StateGraph Implementation)

Implements the OODA loop as a genuine LangGraph StateGraph with:
- 7 named node functions
- Conditional routing edge: check_budget_authority → autonomous OR escalate
- MemorySaver checkpointer for thread persistence
- interrupt() in escalate_to_human so the graph genuinely halts until resumed
- Both action paths converge into log_audit_trail → END
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, TypedDict, Annotated
import operator

import pandas as pd

from config import settings
from .context_builder import ContextBuilder, RiskContextFrame, get_context_builder
from .policy import PolicyEngine, PolicyResult
from .audit_logger import AuditLogger, get_audit_logger
from .actions import ActionTier, ActionStatus

# ── LangGraph imports ─────────────────────────────────────────────────────────
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# AgentState — the single mutable object threaded through all graph nodes
# ──────────────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    # Inputs provided at invocation time
    sku_id: str
    primary_supplier_id: str
    current_inventory: int
    alternative_supplier_ids: list[str]
    trigger_type: str

    # ML prediction outputs (populated by gather_ml_predictions)
    demand_forecast: dict[str, Any]          # raw DemandForecast dict
    supplier_risk_score: float               # LightGBM calibrated probability
    shap_drivers: list[dict[str, Any]]       # top-3 SHAP features from LightGBM
    anomaly_flag: bool                       # LSTM-AE is_anomaly
    reconstruction_error: float              # LSTM-AE reconstruction MSE

    # Context frame (populated by build_risk_context)
    risk_context_frame: dict[str, Any]       # serialised RiskContextFrame.model_dump()

    # Policy decision outputs (populated by reason_over_context)
    policy_result_dict: dict[str, Any]       # serialised PolicyResult.to_dict()

    # Routing & dispatch (populated by check_budget_authority)
    recommended_action_type: str             # first action type in plan
    estimated_cost: float                    # total estimated cost of plan
    tier: str                                # AUTONOMOUS | RECOMMEND_CONFIRM | ESCALATE

    # Execution results (populated by execute_autonomous_action or escalate_to_human)
    human_approval_needed: bool
    human_decision: str | None               # "approved" | "rejected" | None
    action_executed: bool

    # Audit accumulation — uses `operator.add` reducer so each node can append
    audit_entries: Annotated[list[dict[str, Any]], operator.add]

    # Final status written by log_audit_trail
    cycle_status: str                        # "SUCCESS" | "ERROR" | "PENDING_HUMAN"


# ──────────────────────────────────────────────────────────────────────────────
# Node 1: gather_ml_predictions
# Observe — calls TFT, LightGBM, and LSTM-AE predictors.
# Reuses the existing predictor singletons from ContextBuilder; does NOT
# duplicate the prediction logic.
# ──────────────────────────────────────────────────────────────────────────────

def gather_ml_predictions(state: AgentState) -> AgentState:
    """
    OBSERVE node: run all three ML models and store raw outputs in state.
    Uses the shared ContextBuilder instance to access pre-loaded predictors
    and data without duplicating inference code.
    """
    logger.info("[gather_ml_predictions] SKU=%s | Supplier=%s", state["sku_id"], state["primary_supplier_id"])

    cb = get_context_builder()
    supplier_df = _get_orchestrator_data()["supplier_df"]
    demand_df   = _get_orchestrator_data()["demand_df"]

    sku_id              = state["sku_id"]
    primary_supplier_id = state["primary_supplier_id"]
    alt_ids             = state.get("alternative_supplier_ids", [])
    current_inventory   = state.get("current_inventory", 5000)

    # ── TFT Demand Forecast ────────────────────────────────────────────────
    demand_signal = cb._run_demand_forecast(sku_id, demand_df, current_inventory)

    # ── LightGBM Supplier Risk ─────────────────────────────────────────────
    all_supplier_ids = [primary_supplier_id] + alt_ids
    risk_map         = cb._run_risk_predictions(all_supplier_ids, supplier_df)
    primary_risk     = risk_map.get(primary_supplier_id)

    # ── LSTM-AE Anomaly Detection ──────────────────────────────────────────
    anomaly_map  = cb._run_anomaly_detection([primary_supplier_id], supplier_df)
    primary_anon = anomaly_map.get(primary_supplier_id)

    return {
        **state,
        "demand_forecast": demand_signal.model_dump(),
        "supplier_risk_score": primary_risk.risk_score if primary_risk else 0.0,
        "shap_drivers":        primary_risk.shap_drivers if primary_risk else [],
        "anomaly_flag":        primary_anon.is_anomaly if primary_anon else False,
        "reconstruction_error": primary_anon.reconstruction_error if primary_anon else 0.0,
        "audit_entries": [{
            "node": "gather_ml_predictions",
            "sku_id": sku_id,
            "supplier_risk_score": primary_risk.risk_score if primary_risk else 0.0,
            "anomaly_flag": primary_anon.is_anomaly if primary_anon else False,
        }],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Node 2: build_risk_context
# Orient — assembles the full RiskContextFrame from ML outputs + operational data.
# ──────────────────────────────────────────────────────────────────────────────

def build_risk_context(state: AgentState) -> AgentState:
    """
    ORIENT node: assembles a RiskContextFrame using ContextBuilder.build_frame().
    The full frame is serialised to a dict so it is JSON-safe in the graph state.
    """
    logger.info("[build_risk_context] Building frame for SKU=%s", state["sku_id"])

    cb          = get_context_builder()
    data        = _get_orchestrator_data()
    supplier_df = data["supplier_df"]
    demand_df   = data["demand_df"]

    frame: RiskContextFrame = cb.build_frame(
        sku_id=state["sku_id"],
        primary_supplier_id=state["primary_supplier_id"],
        demand_history_df=demand_df,
        supplier_processed_df=supplier_df,
        current_inventory=state.get("current_inventory", 5000),
        alternative_supplier_ids=state.get("alternative_supplier_ids") or None,
    )

    return {
        **state,
        "risk_context_frame": frame.model_dump(),
        "audit_entries": [{"node": "build_risk_context", "overall_risk": frame.overall_risk_level}],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Node 3: reason_over_context
# Decide — runs the PolicyEngine to produce an ActionPlan.
# ──────────────────────────────────────────────────────────────────────────────

def reason_over_context(state: AgentState) -> AgentState:
    """
    DECIDE node: feeds the RiskContextFrame into PolicyEngine.decide_actions()
    and serialises the result into state.
    """
    logger.info("[reason_over_context] Running PolicyEngine for SKU=%s", state["sku_id"])

    from .context_builder import RiskContextFrame
    frame = RiskContextFrame(**state["risk_context_frame"])

    pe = PolicyEngine()
    result: PolicyResult = pe.decide_actions(frame)

    return {
        **state,
        "policy_result_dict": result.to_dict(),
        "audit_entries": [{
            "node": "reason_over_context",
            "num_actions": len(result.actions),
            "reasoning_summary": result.system_reasoning_summary,
        }],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Node 4: check_budget_authority
# Extracts tier routing information from the policy result.
# This was previously buried inside _dispatch() — now it is a first-class node.
# ──────────────────────────────────────────────────────────────────────────────

def check_budget_authority(state: AgentState) -> AgentState:
    """
    Routing node: reads the action plan to determine the highest-priority tier.
    Tier precedence: ESCALATE > RECOMMEND_CONFIRM > AUTONOMOUS.
    """
    logger.info("[check_budget_authority] Evaluating tier for SKU=%s", state["sku_id"])

    actions = state["policy_result_dict"].get("actions", [])
    total_cost = sum(a.get("estimated_cost_usd", 0.0) for a in actions)

    # Determine dominant tier (ESCALATE takes priority over everything)
    tier = "AUTONOMOUS"
    recommended_action_type = ""
    if actions:
        recommended_action_type = actions[0].get("action_type", "")
        for a in actions:
            a_tier = a.get("tier", "AUTONOMOUS")
            if a_tier == "ESCALATE":
                tier = "ESCALATE"
                break
            if a_tier == "RECOMMEND_CONFIRM" and tier == "AUTONOMOUS":
                tier = "RECOMMEND_CONFIRM"

    logger.info("[check_budget_authority] Tier=%s | Cost=$%.2f", tier, total_cost)

    return {
        **state,
        "recommended_action_type": recommended_action_type,
        "estimated_cost": total_cost,
        "tier": tier,
        "audit_entries": [{
            "node": "check_budget_authority",
            "tier": tier,
            "total_cost_usd": total_cost,
        }],
    }


def route_by_tier(state: AgentState) -> str:
    """
    Conditional routing function. Returns the name of the next node.
    Called by add_conditional_edges on check_budget_authority.
    """
    tier = state.get("tier", "AUTONOMOUS")
    if tier == "AUTONOMOUS":
        return "autonomous"
    return "escalate"


# ──────────────────────────────────────────────────────────────────────────────
# Node 5: execute_autonomous_action
# ACT (Tier 1) — mock ERP call, marks action as EXECUTED.
# ──────────────────────────────────────────────────────────────────────────────

def execute_autonomous_action(state: AgentState) -> AgentState:
    """
    Tier 1 path: execute action autonomously with a mock ERP/WMS call.
    In production, replace the logger.debug with a real HTTP call.
    """
    logger.info(
        "[execute_autonomous_action] AUTONOMOUS execute: %s for SKU=%s",
        state.get("recommended_action_type", ""), state["sku_id"],
    )
    logger.debug(
        "MOCK ERP CALL → action=%s | SKU=%s | Supplier=%s | Cost=$%.2f",
        state.get("recommended_action_type"),
        state["sku_id"],
        state["primary_supplier_id"],
        state.get("estimated_cost", 0.0),
    )

    return {
        **state,
        "human_approval_needed": False,
        "human_decision": None,
        "action_executed": True,
        "cycle_status": "SUCCESS",
        "audit_entries": [{
            "node": "execute_autonomous_action",
            "status": "EXECUTED",
            "action_type": state.get("recommended_action_type", ""),
            "cost_usd": state.get("estimated_cost", 0.0),
        }],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Node 6: escalate_to_human
# ACT (Tier 2/3) — calls LangGraph's interrupt() to genuinely pause the graph
# thread. Execution does NOT resume until the approve/reject API endpoint
# calls compiled_app.invoke() with the human decision in the thread config.
# ──────────────────────────────────────────────────────────────────────────────

def escalate_to_human(state: AgentState) -> AgentState:
    """
    Human-in-the-loop escalation node.

    Calls LangGraph interrupt() which genuinely suspends this graph thread.
    The graph will NOT advance to log_audit_trail until:
      1. The approve endpoint calls compiled_app.invoke(
             {"human_decision": "approved"}, config=thread_config
         ), OR
      2. The reject endpoint calls compiled_app.invoke(
             {"human_decision": "rejected"}, config=thread_config
         ).

    The interrupt() call raises a special LangGraph exception that the runtime
    catches; the graph state is persisted by MemorySaver at this exact point.
    """
    logger.info(
        "[escalate_to_human] INTERRUPT: awaiting human decision for SKU=%s | Tier=%s | Cost=$%.2f",
        state["sku_id"], state.get("tier"), state.get("estimated_cost", 0.0),
    )

    # Prepare the payload that will be surfaced to the human reviewer
    interrupt_payload = {
        "type": "human_approval_required",
        "sku_id": state["sku_id"],
        "supplier_id": state["primary_supplier_id"],
        "action_type": state.get("recommended_action_type", ""),
        "tier": state.get("tier", "RECOMMEND_CONFIRM"),
        "estimated_cost_usd": state.get("estimated_cost", 0.0),
        "reasoning": state["policy_result_dict"].get("reasoning_steps", []),
        "supplier_risk_score": state.get("supplier_risk_score", 0.0),
        "anomaly_flag": state.get("anomaly_flag", False),
    }

    # This call halts graph execution. The `human_decision` value is injected
    # by the resume call from the approve/reject API endpoint.
    human_decision: str = interrupt(interrupt_payload)

    logger.info(
        "[escalate_to_human] RESUMED: human_decision=%s for SKU=%s",
        human_decision, state["sku_id"],
    )

    action_executed = human_decision == "approved"

    return {
        **state,
        "human_approval_needed": True,
        "human_decision": human_decision,
        "action_executed": action_executed,
        "cycle_status": "SUCCESS" if action_executed else "REJECTED",
        "audit_entries": [{
            "node": "escalate_to_human",
            "human_decision": human_decision,
            "action_executed": action_executed,
            "action_type": state.get("recommended_action_type", ""),
            "cost_usd": state.get("estimated_cost", 0.0),
        }],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Node 7: log_audit_trail
# Final node — writes to the audit log and sets final cycle_status.
# ──────────────────────────────────────────────────────────────────────────────

def log_audit_trail(state: AgentState) -> AgentState:
    """
    Final convergence node. Both execution paths (autonomous and escalate)
    end here. Writes the complete OODA cycle to the AuditLogger.
    """
    logger.info(
        "[log_audit_trail] Writing audit record for SKU=%s | Status=%s",
        state["sku_id"], state.get("cycle_status", "UNKNOWN"),
    )

    audit_logger: AuditLogger = get_audit_logger()
    audit_logger.log_cycle(
        trigger_type=state.get("trigger_type", "MANUAL"),
        sku_id=state["sku_id"],
        primary_supplier_id=state["primary_supplier_id"],
        risk_context=state.get("risk_context_frame", {}),
        action_plan=state.get("policy_result_dict", {}),
        dispatch_results=state.get("audit_entries", []),
        status=state.get("cycle_status", "UNKNOWN"),
    )

    return {
        **state,
        "audit_entries": [{"node": "log_audit_trail", "written": True}],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Graph Construction
# ──────────────────────────────────────────────────────────────────────────────

def _build_graph() -> StateGraph:
    """Build and compile the LangGraph StateGraph for the OODA loop."""
    graph = StateGraph(AgentState)

    # Register all nodes
    graph.add_node("gather_ml_predictions", gather_ml_predictions)
    graph.add_node("build_risk_context",    build_risk_context)
    graph.add_node("reason_over_context",   reason_over_context)
    graph.add_node("check_budget_authority", check_budget_authority)
    graph.add_node("execute_autonomous_action", execute_autonomous_action)
    graph.add_node("escalate_to_human",     escalate_to_human)
    graph.add_node("log_audit_trail",       log_audit_trail)

    # Linear edges: OBSERVE → ORIENT → DECIDE → ROUTE
    graph.set_entry_point("gather_ml_predictions")
    graph.add_edge("gather_ml_predictions", "build_risk_context")
    graph.add_edge("build_risk_context",    "reason_over_context")
    graph.add_edge("reason_over_context",   "check_budget_authority")

    # Conditional edge: ROUTE → ACT (autonomous OR escalate)
    graph.add_conditional_edges(
        "check_budget_authority",
        route_by_tier,
        {
            "autonomous": "execute_autonomous_action",
            "escalate":   "escalate_to_human",
        },
    )

    # Both ACT paths converge into the audit node, then END
    graph.add_edge("execute_autonomous_action", "log_audit_trail")
    graph.add_edge("escalate_to_human",         "log_audit_trail")
    graph.add_edge("log_audit_trail",           END)

    return graph


# ──────────────────────────────────────────────────────────────────────────────
# Compiled Graph Singleton
# ──────────────────────────────────────────────────────────────────────────────

# SqliteSaver stores graph state persistently in the SQLite database.
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

_sqlite_conn = sqlite3.connect("supplymind.db", check_same_thread=False)
_checkpointer = SqliteSaver(_sqlite_conn)
_compiled_app = None

def get_compiled_app():
    """Return the compiled LangGraph app (singleton)."""
    global _compiled_app
    if _compiled_app is None:
        graph = _build_graph()
        _compiled_app = graph.compile(checkpointer=_checkpointer)
        logger.info("LangGraph OODA graph compiled successfully with SqliteSaver checkpointer.")
    return _compiled_app


# ──────────────────────────────────────────────────────────────────────────────
# Data cache — supplier & demand DataFrames loaded once and shared
# ──────────────────────────────────────────────────────────────────────────────

_data_cache: dict[str, pd.DataFrame] = {}
_last_loaded_mtimes: dict[str, float] = {}

def _load_file_with_formats(base_name: str) -> pd.DataFrame | None:
    extensions = [".parquet", ".pkt", ".pkl", ".csv", ".json"]
    for ext in extensions:
        path = Path(settings.data_processed_dir) / f"{base_name}{ext}"
        if path.exists():
            mtime = os.path.getmtime(path)
            cached_mtime = _last_loaded_mtimes.get(base_name)
            if cached_mtime == mtime and base_name in _data_cache:
                return _data_cache[base_name]
            logger.info("Loading %s%s (mtime=%s)...", base_name, ext, mtime)
            try:
                if ext == ".parquet":
                    df = pd.read_parquet(path)
                elif ext in (".pkt", ".pkl"):
                    df = pd.read_pickle(path)
                elif ext == ".csv":
                    df = pd.read_csv(path)
                elif ext == ".json":
                    df = pd.read_json(path)
                else:
                    continue
                _data_cache[base_name] = df
                _last_loaded_mtimes[base_name] = mtime
                return df
            except Exception as exc:
                logger.error("Failed to load file %s: %s", path, exc)
    return None

def _get_orchestrator_data() -> dict[str, pd.DataFrame]:
    """Load processed data dynamically; reload on modification or check format fallbacks."""
    global _data_cache
    
    # Check if we can reuse the fully processed dataframes in cache
    supplier_mtime = 0.0
    demand_mtime = 0.0
    for ext in [".parquet", ".pkt", ".pkl", ".csv", ".json"]:
        s_path = Path(settings.data_processed_dir) / f"supplier_train{ext}"
        d_path = Path(settings.data_processed_dir) / f"demand_features{ext}"
        if s_path.exists() and supplier_mtime == 0.0:
            supplier_mtime = os.path.getmtime(s_path)
        if d_path.exists() and demand_mtime == 0.0:
            demand_mtime = os.path.getmtime(d_path)

    if (
        "supplier_df" in _data_cache 
        and _last_loaded_mtimes.get("supplier_train") == supplier_mtime 
        and "demand_df" in _data_cache 
        and _last_loaded_mtimes.get("demand_features") == demand_mtime
    ):
        return _data_cache
    
    # 1. Load supplier data
    supplier_df = _load_file_with_formats("supplier_train")
    if supplier_df is not None:
        _data_cache["supplier_df"] = supplier_df
    else:
        if "supplier_df" not in _data_cache:
            _data_cache["supplier_df"] = pd.DataFrame()

    # 2. Load demand data
    demand_df = _load_file_with_formats("demand_features")
    if demand_df is not None:
        df = demand_df.copy()
        if "id" not in df.columns and "store_id" in df.columns:
            df["id"] = df["store_id"].astype(str) + "_" + df.get("item_id", "").astype(str)
        if "id" in df.columns:
            df["id"] = df["id"].astype(str)
        if "time_idx" not in df.columns:
            if "d" in df.columns:
                df["time_idx"] = df["d"].str.extract(r"(\d+)").astype(int)
            elif "date" in df.columns:
                df["time_idx"] = (
                    (pd.to_datetime(df["date"]) - pd.to_datetime(df["date"].min())).dt.days
                )
            else:
                df["time_idx"] = range(len(df))
        if "snap_CA" not in df.columns:
            df["snap_CA"] = 0
        _data_cache["demand_df"] = df
    else:
        if "demand_df" not in _data_cache:
            _data_cache["demand_df"] = pd.DataFrame()

    return _data_cache


# ──────────────────────────────────────────────────────────────────────────────
# Public API — used by api/routes/agent.py and agent/scheduler.py
# ──────────────────────────────────────────────────────────────────────────────

def run_cycle(
    *,
    sku_id: str,
    primary_supplier_id: str,
    current_inventory: int = 5000,
    alternative_supplier_ids: list[str] | None = None,
    trigger_type: str = "MANUAL",
    thread_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute one full OODA cycle via the compiled LangGraph app.

    For AUTONOMOUS actions, runs to completion and returns the final state.
    For RECOMMEND_CONFIRM / ESCALATE actions, the graph halts at
    `escalate_to_human` (via interrupt()) and returns with
    cycle_status="PENDING_HUMAN" and human_approval_needed=True.

    Args:
        sku_id:                    SKU being evaluated.
        primary_supplier_id:       Main supplier for this SKU.
        current_inventory:         Current on-hand units.
        alternative_supplier_ids:  Optional backup supplier IDs.
        trigger_type:              MANUAL | SCHEDULED | EVENT | THRESHOLD.
        thread_id:                 LangGraph thread ID for checkpointing.
                                   Defaults to "<sku_id>_<supplier_id>".
    Returns:
        dict with keys: status, sku_id, primary_supplier_id, context,
                        plan, dispatch_results, human_approval_needed,
                        thread_id.
    """
    logger.info("══ LANGGRAPH OODA CYCLE START | SKU=%s | Trigger=%s ══", sku_id, trigger_type)

    _thread_id = thread_id or f"{sku_id}_{primary_supplier_id}"
    config = {"configurable": {"thread_id": _thread_id}}

    initial_state: AgentState = {
        "sku_id": sku_id,
        "primary_supplier_id": primary_supplier_id,
        "current_inventory": current_inventory,
        "alternative_supplier_ids": alternative_supplier_ids or [],
        "trigger_type": trigger_type,
        # Initialise output fields with safe defaults
        "demand_forecast": {},
        "supplier_risk_score": 0.0,
        "shap_drivers": [],
        "anomaly_flag": False,
        "reconstruction_error": 0.0,
        "risk_context_frame": {},
        "policy_result_dict": {},
        "recommended_action_type": "",
        "estimated_cost": 0.0,
        "tier": "AUTONOMOUS",
        "human_approval_needed": False,
        "human_decision": None,
        "action_executed": False,
        "cycle_status": "UNKNOWN",
        "audit_entries": [],
    }

    compiled = get_compiled_app()
    try:
        final_state = compiled.invoke(initial_state, config=config)

        logger.info(
            "══ LANGGRAPH OODA COMPLETE | SKU=%s | Status=%s | HumanNeeded=%s ══",
            sku_id, final_state.get("cycle_status"), final_state.get("human_approval_needed"),
        )

        return {
            "status": final_state.get("cycle_status", "UNKNOWN"),
            "trigger_type": trigger_type,
            "sku_id": sku_id,
            "primary_supplier_id": primary_supplier_id,
            "context": final_state.get("risk_context_frame", {}),
            "plan": final_state.get("policy_result_dict", {}),
            "dispatch_results": final_state.get("audit_entries", []),
            "human_approval_needed": final_state.get("human_approval_needed", False),
            "tier": final_state.get("tier", "AUTONOMOUS"),
            "thread_id": _thread_id,
        }

    except Exception as exc:
        logger.exception("LangGraph OODA cycle failed for SKU=%s", sku_id)
        get_audit_logger().log_cycle(
            trigger_type=trigger_type,
            sku_id=sku_id,
            primary_supplier_id=primary_supplier_id,
            risk_context={},
            action_plan={},
            dispatch_results=[],
            status="ERROR",
            error_message=str(exc),
        )
        return {
            "status": "ERROR",
            "sku_id": sku_id,
            "error_message": str(exc),
            "thread_id": _thread_id,
        }


def resume_cycle(
    *,
    thread_id: str,
    human_decision: str,  # "approved" | "rejected"
) -> dict[str, Any]:
    """
    Resume a graph thread that was halted at escalate_to_human (via interrupt()).

    Called by the approve/reject API endpoints. Injects the human decision
    into the suspended graph thread and allows it to advance to
    log_audit_trail → END.

    Args:
        thread_id:      The thread ID returned when the cycle was first triggered.
        human_decision: "approved" or "rejected".

    Returns:
        Updated final state dict.
    """
    logger.info("[resume_cycle] Resuming thread=%s with decision=%s", thread_id, human_decision)
    config = {"configurable": {"thread_id": thread_id}}
    compiled = get_compiled_app()

    try:
        # Inject the human decision as the interrupt resume value
        final_state = compiled.invoke(
            {"human_decision": human_decision},
            config=config,
        )

        logger.info(
            "[resume_cycle] Thread=%s resumed successfully | Status=%s",
            thread_id, final_state.get("cycle_status"),
        )
        return {
            "status": final_state.get("cycle_status", "UNKNOWN"),
            "human_decision": human_decision,
            "action_executed": final_state.get("action_executed", False),
            "thread_id": thread_id,
        }

    except Exception as exc:
        logger.exception("Failed to resume graph thread=%s", thread_id)
        return {
            "status": "ERROR",
            "error_message": str(exc),
            "thread_id": thread_id,
        }


def run_batch(
    sku_supplier_pairs: list[dict[str, Any]],
    trigger_type: str = "SCHEDULED",
) -> list[dict[str, Any]]:
    """
    Run multiple OODA cycles in sequence (e.g., daily scheduled audit).
    Each entry must have: sku_id, primary_supplier_id.
    Optional: current_inventory, alternative_supplier_ids.
    """
    results = []
    total = len(sku_supplier_pairs)
    for i, pair in enumerate(sku_supplier_pairs, 1):
        logger.info("Batch cycle %d/%d: SKU=%s", i, total, pair.get("sku_id"))
        result = run_cycle(
            sku_id=pair["sku_id"],
            primary_supplier_id=pair["primary_supplier_id"],
            current_inventory=pair.get("current_inventory", 5000),
            alternative_supplier_ids=pair.get("alternative_supplier_ids"),
            trigger_type=trigger_type,
        )
        results.append(result)
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Legacy compatibility shim
# Keeps the old get_orchestrator() call sites in scheduler.py working
# while the API routes migrate to the new run_cycle() function directly.
# ──────────────────────────────────────────────────────────────────────────────

class _OrchestratorShim:
    """
    Thin compatibility wrapper so agent/scheduler.py can still call
    self.orchestrator.run_batch() without modification.
    """
    def run_batch(self, pairs: list[dict[str, Any]], trigger_type: str = "SCHEDULED") -> list[dict[str, Any]]:
        return run_batch(pairs, trigger_type=trigger_type)

    def _load_supplier_data(self) -> pd.DataFrame:
        return _get_orchestrator_data()["supplier_df"]

    def _load_demand_data(self) -> pd.DataFrame:
        return _get_orchestrator_data()["demand_df"]

    def get_available_supplier_ids(self, n: int = 10) -> list[str]:
        df = self._load_supplier_data()
        if df.empty:
            return []
        return df["supplier_id"].unique().tolist()[:n]

    def get_available_sku_ids(self, n: int = 5) -> list[str]:
        df = self._load_demand_data()
        if df.empty:
            return []
        return df["id"].unique().tolist()[:n]

    @property
    def audit_log(self) -> list[dict[str, Any]]:
        return get_audit_logger().get_recent(n=100)

    @property
    def audit_stats(self) -> dict[str, Any]:
        return get_audit_logger().get_stats()


AgentOrchestrator = _OrchestratorShim
_shim: _OrchestratorShim | None = None

def get_orchestrator() -> _OrchestratorShim:
    """Return the legacy-compatible orchestrator shim."""
    global _shim
    if _shim is None:
        _shim = _OrchestratorShim()
    return _shim
