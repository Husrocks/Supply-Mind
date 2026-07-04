import type { SupplierRisk, DemandForecast, InventorySku, AgentAction, AuditEntry, ModelPerformance, SchedulerHealth, SupplierOnboarding, SupplyFlow, WarehouseNode, NetworkLink } from '../types';

export const queryKeys = {
  riskContext: ['risk-context'] as const,
  inventory: ['inventory-risk'] as const,
  pendingActions: ['agent-actions', 'pending'] as const,
  allActions: ['agent-actions', 'all'] as const,
  auditLog: ['audit-log'] as const,
  modelPerformance: ['model-performance'] as const,
  schedulerHealth: ['scheduler-health'] as const,
  onboarding: ['supplier-onboarding'] as const,
  settings: ['settings'] as const,
  supplierDetail: (id: string) => ['supplier-detail', id] as const,
  skuDetail: (id: string) => ['sku-detail', id] as const,
};

export interface RiskContextData {
  context_id: string;
  generated_at: string;
  overall_risk_score: number;
  anomaly_count: number;
  agent_triggered: boolean;
  supplier_risks: SupplierRisk[];
  demand_forecasts: DemandForecast[];
  supply_flows?: SupplyFlow[];
  warehouse_nodes?: WarehouseNode[];
  network_links?: NetworkLink[];
  risk_trends?: Record<string, number[]>;
}

export type {
  SupplierRisk,
  DemandForecast,
  InventorySku,
  AgentAction,
  AuditEntry,
  ModelPerformance,
  SchedulerHealth,
  SupplierOnboarding,
};
