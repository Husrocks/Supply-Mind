import type { SupplierRisk, InventorySku, AgentAction, AlertItem } from '../types';

export function buildAlerts(
  suppliers: SupplierRisk[],
  inventory: InventorySku[],
  pending: AgentAction[],
): AlertItem[] {
  const alerts: AlertItem[] = [];

  suppliers
    .filter((s) => s.risk_score >= 0.7)
    .forEach((s) => {
      alerts.push({
        id: `sup-${s.supplier_id}`,
        severity: s.risk_score >= 0.85 ? 'critical' : 'elevated',
        title: `High risk: ${s.supplier_name}`,
        message: s.reasoning,
        timestamp: new Date().toISOString(),
        supplierId: s.supplier_id,
      });
    });

  inventory
    .filter((s) => s.status === 'CRITICAL')
    .forEach((s) => {
      alerts.push({
        id: `sku-${s.sku_id}`,
        severity: 'critical',
        title: `Stockout risk: ${s.sku_id}`,
        message: `${s.days_to_stockout.toFixed(1)} days to stockout`,
        timestamp: new Date().toISOString(),
        skuId: s.sku_id,
      });
    });

  pending.forEach((a) => {
    alerts.push({
      id: `act-${a.action_id}`,
      severity: 'elevated',
      title: `Pending approval: ${a.action_type}`,
      message: a.reasoning,
      timestamp: a.created_at,
    });
  });

  return alerts.slice(0, 12);
}

export function buildSkuSparklines(skus: InventorySku[]): Record<string, number[]> {
  const map: Record<string, number[]> = {};
  skus.forEach((sku) => {
    const actuals = sku.forecast_history
      .filter((h) => h.actual !== null)
      .map((h) => h.actual as number);
    if (actuals.length >= 2) {
      map[sku.sku_id] = actuals;
    }
  });
  return map;
}

export function buildSupplierSparklines(
  suppliers: SupplierRisk[],
  riskTrends?: Record<string, number[]>,
): Record<string, number[]> {
  const map: Record<string, number[]> = {};
  suppliers.forEach((s) => {
    const trend = riskTrends?.[s.supplier_id];
    if (trend && trend.length >= 2) {
      map[s.supplier_id] = trend;
    }
  });
  return map;
}

export function benchmarkMetrics(
  suppliers: SupplierRisk[],
  pending: AgentAction[],
  allActions: AgentAction[],
  riskTrends?: Record<string, number[]>,
) {
  const atRisk = suppliers.filter((s) => s.risk_score >= 0.4).length;
  const avgRisk = suppliers.length
    ? suppliers.reduce((a, s) => a + s.risk_score, 0) / suppliers.length
    : 0;

  const priorAvg = (() => {
    if (!riskTrends) return null;
    const vals: number[] = [];
    for (const s of suppliers) {
      const t = riskTrends[s.supplier_id];
      if (t && t.length >= 2) vals.push(t[t.length - 2]);
    }
    return vals.length ? (vals.reduce((a, v) => a + v, 0) / vals.length) * 100 : null;
  })();

  const weekAgo = Date.now() - 7 * 86400000;
  const thisWeekCost = allActions
    .filter((a) => new Date(a.created_at).getTime() >= weekAgo)
    .reduce((sum, a) => sum + (a.estimated_impact?.cost_delta ?? 0), 0);
  const priorWeekCost = allActions
    .filter((a) => {
      const t = new Date(a.created_at).getTime();
      return t >= weekAgo - 7 * 86400000 && t < weekAgo;
    })
    .reduce((sum, a) => sum + (a.estimated_impact?.cost_delta ?? 0), 0);

  return [
    { label: 'At-risk suppliers', current: atRisk, previous: null, invertDelta: true },
    { label: 'Avg disruption prob.', current: avgRisk * 100, previous: priorAvg, format: (v: number) => `${v.toFixed(1)}%`, invertDelta: true },
    { label: 'Pending approvals', current: pending.length, previous: null, invertDelta: true },
    { label: 'Action cost (7d)', current: thisWeekCost, previous: priorWeekCost > 0 ? priorWeekCost : null, format: (v: number) => `$${v.toLocaleString()}`, invertDelta: true },
  ];
}
