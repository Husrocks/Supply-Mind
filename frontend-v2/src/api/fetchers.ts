import {
  getAuditLog,
  getInventoryRisk,
  getModelPerformance,
  getPendingActions,
  getAllActions,
  getRiskContext,
  getSchedulerStatus,
  getOnboardingList,
} from './client';
import type { RiskContextData } from './queries';

export async function fetchRiskContext(): Promise<RiskContextData> {
  return getRiskContext();
}

export async function fetchInventory() {
  return getInventoryRisk();
}

export async function fetchPendingActions() {
  return getPendingActions();
}

export async function fetchAllActions() {
  return getAllActions();
}

export async function fetchAuditLog() {
  return getAuditLog();
}

export async function fetchModelPerformance() {
  return getModelPerformance();
}

export async function fetchSchedulerHealth() {
  return getSchedulerStatus();
}

export async function fetchOnboarding(status?: string) {
  return getOnboardingList(status);
}
