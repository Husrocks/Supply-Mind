"""
SupplyMind — Interactive Features Schemas
Provides Pydantic validation schemas for What-If simulator, Smart Reorders,
Supplier Disruption, Explainability, and Data-Grounded Assistant.
"""

from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────────────
# 1. What-If Simulator Schemas
# ──────────────────────────────────────────────────────────────────────────────

class WhatIfRequest(BaseModel):
    sku_id: str = Field(..., description="Target SKU identifier")
    supplier_id: str | None = Field(None, description="Primary supplier identifier (optional)")
    demand_change_pct: float = Field(0.0, ge=-50.0, le=150.0, description="Percentage change in daily demand (-50% to +150%)")
    lead_time_increase_days: int = Field(0, ge=0, le=90, description="Additional days added to supplier lead time")
    inventory_override: int | None = Field(None, ge=0, description="Optional override for current on-hand units")
    supplier_disruption_pct: float = Field(0.0, ge=0.0, le=100.0, description="Disruption percentage / capacity reduction (0% - 100%)")


class DailyTrajectoryPoint(BaseModel):
    day: int
    baseline_inventory: float
    simulated_inventory: float


class DriverAttribution(BaseModel):
    factor: str
    impact_days: float
    direction: Literal["reduces_runway", "increases_runway", "neutral"]
    description: str


class WhatIfResponse(BaseModel):
    sku_id: str
    supplier_id: str
    supplier_name: str
    assumptions_summary: str
    
    # Baseline Metrics
    baseline_inventory: float
    baseline_daily_demand: float
    baseline_lead_time_days: int
    baseline_days_to_stockout: float
    baseline_risk_tier: str
    baseline_reorder_point: int
    
    # Simulated Metrics
    simulated_inventory: float
    simulated_daily_demand: float
    simulated_effective_lead_time_days: int
    simulated_days_to_stockout: float
    simulated_risk_tier: str
    simulated_reorder_point: int
    
    # Deltas & Comparisons
    delta_days_to_stockout: float
    coverage_gap_days: float
    stockout_day: int | None
    is_stockout_within_replenishment: bool
    
    # Driver Breakdown & Explanation
    drivers: list[DriverAttribution]
    primary_driver_explanation: str
    
    # Trajectory chart points (30-day lookahead)
    trajectory: list[DailyTrajectoryPoint]
    
    # Timestamp & Mode
    timestamp: str
    is_simulated_estimate: bool = True


# ──────────────────────────────────────────────────────────────────────────────
# 2. Smart Reorder Recommendations Schemas
# ──────────────────────────────────────────────────────────────────────────────

class SupplierOption(BaseModel):
    supplier_id: str
    supplier_name: str
    risk_score: float
    risk_tier: str
    lead_time_days: int
    estimated_unit_cost: float
    is_preferred: bool
    capacity_status: str


class ReorderRecommendationItem(BaseModel):
    sku_id: str
    category: str
    current_inventory: int
    units_in_transit: int
    daily_demand: float
    demand_uncertainty_spread: float
    lead_time_days: int
    safety_stock: int
    reorder_point: int
    suggested_order_qty: int
    days_to_stockout: float
    expected_stockout_date: str
    criticality: Literal["CRITICAL", "ELEVATED", "NORMAL"]
    preferred_supplier_id: str
    preferred_supplier_name: str
    preferred_supplier_risk_score: float
    preferred_supplier_risk_tier: str
    explanation: str
    status: Literal["PENDING", "REVIEWED", "DISMISSED"]
    review_notes: str | None = None
    alternative_suppliers: list[SupplierOption] = Field(default_factory=list)


class ReorderStatusUpdateRequest(BaseModel):
    status: Literal["PENDING", "REVIEWED", "DISMISSED"]
    notes: str | None = None
    updated_by: str | None = "InventoryPlanner"


class ReorderSummaryResponse(BaseModel):
    total_skus_evaluated: int
    actionable_reorders_count: int
    critical_stockout_count: int
    elevated_count: int
    total_suggested_units: int
    estimated_reorder_budget_usd: float
    recommendations: list[ReorderRecommendationItem]


# ──────────────────────────────────────────────────────────────────────────────
# 3. Supplier Disruption Simulator Schemas
# ──────────────────────────────────────────────────────────────────────────────

class DisruptionRequest(BaseModel):
    supplier_id: str = Field(..., description="ID of supplier to disrupt")
    disruption_type: Literal["SHUTDOWN", "DELAY", "CAPACITY_CUT"] = "SHUTDOWN"
    duration_days: int = Field(30, ge=1, le=180, description="Duration of disruption in days")
    severity_pct: float = Field(100.0, ge=10.0, le=100.0, description="Severity percentage (10-100%)")


class AffectedSkuItem(BaseModel):
    sku_id: str
    current_units_on_hand: int
    daily_consumption: float
    days_of_stock_remaining: float
    stockout_expected_within_disruption: bool
    stockout_day: int | None
    projected_shortfall_units: int
    estimated_value_exposure_usd: float


class MitigationRecommendation(BaseModel):
    title: str
    priority: Literal["HIGH", "MEDIUM", "LOW"]
    action_type: str
    description: str
    estimated_risk_mitigation: str
    trade_off: str


class DisruptionResponse(BaseModel):
    supplier_id: str
    supplier_name: str
    disruption_type: str
    duration_days: int
    severity_pct: float
    
    # Pre vs Post Supplier Risk
    baseline_risk_score: float
    baseline_risk_tier: str
    disrupted_risk_score: float
    disrupted_risk_tier: str
    
    # Network Exposure
    total_affected_skus: int
    critical_skus_count: int
    total_inventory_exposure_usd: float
    total_shortfall_units: int
    affected_skus: list[AffectedSkuItem]
    
    # Candidate Alternatives
    alternative_candidates: list[SupplierOption]
    
    # Recovery Actions
    recommended_mitigations: list[MitigationRecommendation]
    timestamp: str


# ──────────────────────────────────────────────────────────────────────────────
# 4. Explainable ML Schemas
# ──────────────────────────────────────────────────────────────────────────────

class ShapFactorExplanation(BaseModel):
    feature: str
    display_name: str
    raw_value: float | None
    shap_impact: float
    direction: Literal["increases_risk", "decreases_risk", "neutral"]
    human_explanation: str


class SupplierExplainabilityResponse(BaseModel):
    supplier_id: str
    supplier_name: str
    model_name: str
    calibrated_risk_score: float
    risk_tier: str
    plain_english_summary: str
    attribution_disclaimer: str
    
    # Detailed drivers
    shap_drivers: list[ShapFactorExplanation]
    
    # Anomaly evidence (LSTM-AE)
    is_anomaly: bool
    reconstruction_mse: float
    anomaly_threshold_mse: float
    anomaly_explanation: str
    
    # Operational parameters
    on_time_delivery_rate: float
    lead_time_variance: float
    quality_failure_rate: float
    geopolitical_risk: float
    
    data_timestamp: str
    prediction_timestamp: str


class SkuExplainabilityResponse(BaseModel):
    sku_id: str
    model_name: str
    forecast_horizon_days: int
    p05_total_demand: float
    p50_total_demand: float
    p95_total_demand: float
    uncertainty_spread: float
    relative_uncertainty_pct: float
    uncertainty_interpretation: str
    daily_quantiles: list[dict[str, Any]]
    prediction_timestamp: str

    # Frontend convenience & compatibility fields
    p05_demand: float | None = None
    p50_demand: float | None = None
    p95_demand: float | None = None
    uncertainty_ratio: float | None = None
    plain_english_summary: str | None = None
    methodology_note: str | None = None
    model_confidence_tier: str | None = None
    forecast_timestamp: str | None = None


# ──────────────────────────────────────────────────────────────────────────────
# 5. Ask SupplyMind (AI Assistant) Schemas
# ──────────────────────────────────────────────────────────────────────────────

class AssistantCitation(BaseModel):
    title: str
    entity_type: Literal["supplier", "sku", "recommendation", "simulation"]
    entity_id: str
    url: str
    badge_label: str


class AssistantMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AssistantChatRequest(BaseModel):
    question: str
    history: list[AssistantMessage] = Field(default_factory=list)


class AssistantChatResponse(BaseModel):
    answer: str
    intent_detected: str
    confidence: float
    citations: list[AssistantCitation]
    suggested_followups: list[str]
    timestamp: str
    mode: Literal["grounded_local", "llm_augmented"]
