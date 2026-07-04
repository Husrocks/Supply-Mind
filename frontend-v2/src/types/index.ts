export interface ShapDriver {
  feature: string;
  value: number;
  impact: number;
  direction: 'increases_risk' | 'decreases_risk';
}

export interface SupplierContext {
  supplier_id: string;
  risk_score: number;
  risk_level: 'NORMAL' | 'ELEVATED' | 'HIGH' | 'CRITICAL' | 'UNKNOWN';
  is_anomaly: boolean;
  reconstruction_error: number;
  shap_drivers: ShapDriver[];
  avg_lead_time_days: number;
  on_time_delivery_pct: number;
  po_acceptance_rate: number;
  lead_time_slope_6w: number;
  unit_cost_estimate: number;
}

export interface SupplierRisk {
  supplier_id: string;
  supplier_name: string;
  risk_score: number;
  risk_tier: string;
  geopolitical_factor: number;
  lead_time_variance: number;
  quality_failure_rate: number;
  concentration_ratio: number;
  reasoning: string;
  country_code?: string | null;
  geographic_risk_region?: string | null;
  is_anomaly?: boolean;
  shap_drivers?: ShapDriver[];
  avg_lead_time_days?: number;
  on_time_delivery_pct?: number;
  po_acceptance_rate?: number;
  lead_time_slope_6w?: number;
  unit_cost_estimate?: number;
}

export interface DemandForecast {
  sku_id: string;
  sku_name: string;
  forecast_units: number;
  actual_units: number | null;
  forecast_horizon_days: number;
  confidence_lower: number;
  confidence_upper: number;
  mape: number | null;
  model_used: string;
  category?: string;
}

export interface SupplyFlow {
  supplier_id: string;
  supplier_name: string;
  category: string;
  warehouse: string;
  volume: number;
  risk_score: number;
}

export interface WarehouseNode {
  id: string;
  name: string;
  type: string;
}

export interface NetworkLink {
  source: string;
  target: string;
  volume?: number;
}

export interface ForecastHistoryPoint {
  date: string;
  actual: number | null;
  p50: number | null;
  p05: number | null;
  p95: number | null;
}

export interface InventorySku {
  sku_id: string;
  days_to_stockout: number;
  uncertainty_spread: number;
  current_inventory: number;
  status: string;
  forecast_history: ForecastHistoryPoint[];
}

export interface AgentAction {
  action_id: string;
  action_plan_id: string;
  action_type: string;
  status: string;
  trigger_type: string;  // MANUAL | SCHEDULED | EVENT | THRESHOLD
  sku_id: string;
  supplier_id: string;
  payload: Record<string, unknown>;
  reasoning: string;
  confidence_score: number;
  estimated_impact: { cost_delta?: number; risk_reduction?: number; lead_time_change?: number };
  created_at: string;
  updated_at: string;
}

export interface AuditEntry {
  action_id: number;
  action_plan_id: string;
  action_type: string;
  status: string;
  sku_id: string;
  supplier_id: string;
  estimated_cost_usd: number;
  reasoning: string;
  timestamp: string;
}

export interface ModelPerformance {
  tft: { val_wrmsse: number; history: { date: string; wrmsse: number }[] };
  lightgbm: { pr_auc: number; calibration_curve: { predicted: number; actual: number }[] };
  lstm_ae: { current_threshold: number; recent_errors: { supplier_id: string; error: number }[] };
}

export interface SchedulerJob {
  id: string;
  name: string;
  next_run: string;
}

export interface SchedulerHealth {
  status?: string;
  running: boolean;
  scheduler_running: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  last_trigger_type: string | null;
  scheduler_jobs?: SchedulerJob[];
}

export interface SupplierNode {
  id: string;
  name: string;
  risk_score: number;
  val: number;
}

export interface SupplierLink {
  source: string;
  target: string;
}

export type RiskAccent = 'emerald' | 'amber' | 'rose' | 'indigo' | 'cyan';

export interface AlertItem {
  id: string;
  severity: 'critical' | 'elevated' | 'info';
  title: string;
  message: string;
  timestamp: string;
  supplierId?: string;
  skuId?: string;
}

// ── Supplier Onboarding Types ─────────────────────────────────────────────────

export interface SupplierOnboarding {
  id: number;
  supplier_id: string;
  supplier_name: string;
  status: 'PENDING_REVIEW' | 'IN_PROBATION' | 'APPROVED' | 'REJECTED';
  application_date: string;
  probation_start_date: string | null;
  probation_end_date: string | null;
  days_remaining: number | null;
  probation_progress_pct: number;
  probation_on_time_rate: number;
  probation_rejection_rate: number;
  probation_po_count: number;
  reference_check_status: string;
  geographic_risk_region: string | null;
  credentials_data: Record<string, unknown>;
  capacity_info: Record<string, unknown>;
  reviewed_by: string | null;
  review_notes: string | null;
  auto_approve_threshold_met: boolean;
  auto_reject_threshold_triggered: boolean;
}

export interface OnboardRequest {
  supplier_id: string;
  supplier_name: string;
  credentials_data?: Record<string, unknown>;
  geographic_risk_region?: string;
  capacity_info?: Record<string, unknown>;
  reference_check_status?: string;
}
