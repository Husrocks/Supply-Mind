import { useState } from 'react';
import { 
  ShoppingCart, Download, AlertTriangle, 
  Search, XCircle, Clock, 
  Layers, Check, Eye 
} from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';

import { useReorderRecommendations, useUpdateReorderStatusMutation } from '../hooks/useDashboardQueries';
import { getReorderExportUrl } from '../api/client';
import { GlassCard } from '../components/ui/GlassCard';
import { Stagger, StaggerItem } from '../components/motion/Stagger';
import { ViewSkeleton } from '../components/ui/ViewSkeleton';

export default function SmartReorder() {
  const [criticalityFilter, setCriticalityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedSkuDetail, setSelectedSkuDetail] = useState<any | null>(null);

  const { data: summary, isLoading, refetch } = useReorderRecommendations({
    criticality: criticalityFilter !== 'ALL' ? criticalityFilter : undefined,
    status: statusFilter !== 'ALL' ? statusFilter : undefined,
    search: searchQuery || undefined,
  });

  const updateStatusMutation = useUpdateReorderStatusMutation();

  const handleUpdateStatus = async (skuId: string, status: 'REVIEWED' | 'DISMISSED') => {
    try {
      await updateStatusMutation.mutateAsync({
        skuId,
        status,
        notes: `Marked as ${status.toLowerCase()} by procurement planner`,
      });
      toast.success(`SKU ${skuId} marked as ${status.toLowerCase()}`);
      refetch();
    } catch {
      toast.error('Failed to update status.');
    }
  };

  const handleExportCsv = () => {
    const url = getReorderExportUrl();
    window.open(url, '_blank');
  };

  if (isLoading && !summary) {
    return <ViewSkeleton />;
  }

  const items = summary?.recommendations ?? [];

  return (
    <div className="h-full overflow-y-auto p-5 lg:p-6 space-y-6 max-w-content mx-auto">
      <Stagger className="space-y-6">
        
        {/* Header Block */}
        <StaggerItem className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-hairline">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-xl bg-accent-indigo/10 border border-accent-indigo/30 text-accent-indigo">
                <ShoppingCart size={20} />
              </div>
              <h1 className="text-xl font-semibold text-ink">Smart Reorder Recommendations</h1>
            </div>
            <p className="text-xs text-body mt-1">
              Data-grounded replenishment triggers calculated from TFT demand forecasts and supplier lead times.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleExportCsv}
              className="btn-secondary !h-9 text-xs flex items-center gap-1.5"
              title="Download CSV report with formula documentation"
            >
              <Download size={14} />
              Export CSV
            </button>
          </div>
        </StaggerItem>

        {/* KPI Summary Cards */}
        {summary && (
          <StaggerItem className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            
            {/* Total Actionable */}
            <GlassCard className="p-4">
              <div className="flex items-center justify-between text-muted text-xs mb-1">
                <span>Actionable Replenishments</span>
                <ShoppingCart size={15} />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono text-ink">
                  {summary.actionable_reorders_count}
                </span>
                <span className="text-xs text-muted">of {summary.total_skus_evaluated} SKUs</span>
              </div>
              <div className="mt-2 text-[11px] text-muted">
                Items where Net Inventory is at or below Reorder Point.
              </div>
            </GlassCard>

            {/* Critical Stockouts */}
            <GlassCard className="p-4">
              <div className="flex items-center justify-between text-muted text-xs mb-1">
                <span>Critical Stockout Alerts</span>
                <AlertTriangle size={15} className="text-risk-high" />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono text-risk-high">
                  {summary.critical_stockout_count}
                </span>
                <span className="text-xs text-muted">SKUs</span>
              </div>
              <div className="mt-2 text-[11px] text-risk-high">
                Stockout runway is shorter than standard supplier lead time.
              </div>
            </GlassCard>

            {/* Suggested Units */}
            <GlassCard className="p-4">
              <div className="flex items-center justify-between text-muted text-xs mb-1">
                <span>Total Suggested Units</span>
                <Layers size={15} />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono text-ink">
                  {summary.total_suggested_units.toLocaleString()}
                </span>
                <span className="text-xs text-muted">units</span>
              </div>
              <div className="mt-2 text-[11px] text-muted">
                30-day economic batch coverage target.
              </div>
            </GlassCard>

            {/* Estimated Budget */}
            <GlassCard className="p-4">
              <div className="flex items-center justify-between text-muted text-xs mb-1">
                <span>Estimated Capital Required</span>
                <Clock size={15} />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono text-ink">
                  ${summary.estimated_reorder_budget_usd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
              <div className="mt-2 text-[11px] text-muted">
                Based on verified supplier catalog unit pricing.
              </div>
            </GlassCard>

          </StaggerItem>
        )}

        {/* Filter & Search Bar */}
        <StaggerItem>
          <GlassCard className="p-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              
              <div className="flex items-center gap-2 flex-1 min-w-[240px]">
                <div className="relative w-full max-w-sm">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
                  <input
                    type="text"
                    placeholder="Search SKU or preferred vendor..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-slate-900/60 border border-hairline rounded-lg pl-9 pr-3 py-1.5 text-xs text-ink focus:outline-none focus:border-accent-indigo"
                  />
                </div>
              </div>

              <div className="flex items-center gap-3">
                {/* Criticality Filter */}
                <div className="flex items-center gap-1.5 text-xs">
                  <span className="text-muted text-[11px]">Criticality:</span>
                  {['ALL', 'CRITICAL', 'ELEVATED', 'NORMAL'].map((crit) => (
                    <button
                      key={crit}
                      onClick={() => setCriticalityFilter(crit)}
                      className={clsx(
                        'px-2.5 py-1 rounded-lg text-xs font-medium transition-colors border',
                        criticalityFilter === crit
                          ? 'bg-accent-indigo text-white border-accent-indigo'
                          : 'bg-surface-elevated text-body border-hairline hover:text-ink'
                      )}
                    >
                      {crit}
                    </button>
                  ))}
                </div>

                {/* Status Filter */}
                <div className="flex items-center gap-1.5 text-xs border-l border-hairline pl-3">
                  <span className="text-muted text-[11px]">Status:</span>
                  {['ALL', 'PENDING', 'REVIEWED', 'DISMISSED'].map((st) => (
                    <button
                      key={st}
                      onClick={() => setStatusFilter(st)}
                      className={clsx(
                        'px-2.5 py-1 rounded-lg text-xs font-medium transition-colors border',
                        statusFilter === st
                          ? 'bg-accent-indigo text-white border-accent-indigo'
                          : 'bg-surface-elevated text-body border-hairline hover:text-ink'
                      )}
                    >
                      {st}
                    </button>
                  ))}
                </div>
              </div>

            </div>
          </GlassCard>
        </StaggerItem>

        {/* Reorder Recommendations Table */}
        <StaggerItem>
          <GlassCard accent="indigo" className="!p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-hairline bg-surface-elevated/40 text-muted uppercase tracking-wider font-semibold text-[10px]">
                    <th className="p-3.5 pl-5">SKU & Category</th>
                    <th className="p-3.5">Net Inventory</th>
                    <th className="p-3.5">Daily Demand</th>
                    <th className="p-3.5">Safety Stock</th>
                    <th className="p-3.5">Reorder Point</th>
                    <th className="p-3.5">Suggested Qty</th>
                    <th className="p-3.5">Runway</th>
                    <th className="p-3.5">Preferred Supplier</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5 pr-5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-hairline">
                  {items.map((it: any) => (
                    <tr 
                      key={it.sku_id}
                      className={clsx(
                        'hover:bg-surface-elevated/40 transition-colors',
                        it.criticality === 'CRITICAL' && 'bg-rose-950/10'
                      )}
                    >
                      <td className="p-3.5 pl-5">
                        <div className="font-mono font-semibold text-ink">{it.sku_id}</div>
                        <span className="text-[10px] text-muted uppercase">{it.category}</span>
                      </td>

                      <td className="p-3.5 font-mono">
                        <span className="font-semibold text-slate-200">{it.current_inventory.toLocaleString()}</span>
                        {it.units_in_transit > 0 && (
                          <span className="text-[10px] text-muted block">+{it.units_in_transit.toLocaleString()} transit</span>
                        )}
                      </td>

                      <td className="p-3.5 font-mono text-slate-300">
                        {(it.daily_demand ?? 0).toFixed(1)}/day
                      </td>

                      <td className="p-3.5 font-mono text-slate-300">
                        {it.safety_stock.toLocaleString()}
                      </td>

                      <td className="p-3.5 font-mono">
                        <span className="font-semibold text-amber-400">{it.reorder_point.toLocaleString()}</span>
                      </td>

                      <td className="p-3.5">
                        {it.suggested_order_qty > 0 ? (
                          <span className="font-mono font-bold text-accent-indigo bg-accent-indigo/10 border border-accent-indigo/30 px-2 py-0.5 rounded">
                            {it.suggested_order_qty.toLocaleString()}
                          </span>
                        ) : (
                          <span className="text-muted font-mono">—</span>
                        )}
                      </td>

                      <td className="p-3.5 font-mono">
                        <span className={clsx(
                          'font-semibold',
                          it.criticality === 'CRITICAL' ? 'text-risk-high' :
                          it.criticality === 'ELEVATED' ? 'text-risk-medium' :
                          'text-risk-low'
                        )}>
                          {it.days_to_stockout}d
                        </span>
                        <span className="text-[10px] text-muted block">{it.expected_stockout_date}</span>
                      </td>

                      <td className="p-3.5">
                        <div className="text-slate-200 font-medium truncate max-w-[150px]">{it.preferred_supplier_name}</div>
                        <span className={clsx(
                          'text-[9px] font-mono px-1.5 py-0.2 rounded font-semibold uppercase',
                          it.preferred_supplier_risk_tier === 'HIGH' || it.preferred_supplier_risk_tier === 'CRITICAL'
                            ? 'bg-rose-900/30 text-risk-high'
                            : 'bg-emerald-900/30 text-risk-low'
                        )}>
                          {it.preferred_supplier_risk_score * 100}% {it.preferred_supplier_risk_tier}
                        </span>
                      </td>

                      <td className="p-3.5">
                        <span className={clsx(
                          'text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase border',
                          it.status === 'REVIEWED' ? 'bg-emerald-900/20 text-emerald-400 border-emerald-700/40' :
                          it.status === 'DISMISSED' ? 'bg-slate-800 text-slate-400 border-slate-700' :
                          'bg-amber-900/20 text-amber-400 border-amber-700/40'
                        )}>
                          {it.status}
                        </span>
                      </td>

                      <td className="p-3.5 pr-5 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => setSelectedSkuDetail(it)}
                            className="w-8 h-8 sm:w-9 sm:h-9 flex items-center justify-center rounded-lg bg-surface-elevated text-muted hover:text-ink transition-colors border border-hairline touch-action-manipulation"
                            title="Inspect details & alternative suppliers"
                            aria-label="Inspect SKU details"
                          >
                            <Eye size={15} />
                          </button>
                          {it.status === 'PENDING' && (
                            <>
                              <button
                                onClick={() => handleUpdateStatus(it.sku_id, 'REVIEWED')}
                                className="w-8 h-8 sm:w-9 sm:h-9 flex items-center justify-center rounded-lg bg-emerald-900/20 text-emerald-400 hover:bg-emerald-900/40 transition-colors border border-emerald-700/30 touch-action-manipulation"
                                title="Mark as Reviewed"
                                aria-label="Mark as Reviewed"
                              >
                                <Check size={15} />
                              </button>
                              <button
                                onClick={() => handleUpdateStatus(it.sku_id, 'DISMISSED')}
                                className="w-8 h-8 sm:w-9 sm:h-9 flex items-center justify-center rounded-lg bg-slate-800 text-slate-400 hover:text-rose-400 transition-colors border border-hairline touch-action-manipulation"
                                title="Dismiss Recommendation"
                                aria-label="Dismiss Recommendation"
                              >
                                <XCircle size={15} />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}

                  {items.length === 0 && (
                    <tr>
                      <td colSpan={10} className="p-8 text-center text-muted text-xs">
                        No replenishment recommendations match the current filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </GlassCard>
        </StaggerItem>

        {/* SKU Detail Drawer / Modal */}
        {selectedSkuDetail && (
          <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-surface border border-hairline rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
              
              <div className="flex items-center justify-between pb-3 border-b border-hairline">
                <div>
                  <h3 className="text-base font-semibold text-ink flex items-center gap-2">
                    <ShoppingCart size={16} className="text-accent-indigo" />
                    Reorder Dossier: {selectedSkuDetail.sku_id}
                  </h3>
                  <p className="text-xs text-muted mt-0.5">
                    Category: {selectedSkuDetail.category} | Status: {selectedSkuDetail.status}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedSkuDetail(null)}
                  className="p-1.5 rounded-full bg-surface-elevated text-muted hover:text-ink"
                >
                  <XCircle size={18} />
                </button>
              </div>

              {/* Recommendation Narrative */}
              <div className="p-3.5 rounded-xl bg-accent-indigo/10 border border-accent-indigo/30">
                <span className="text-[10px] uppercase font-bold text-accent-indigo tracking-wider block mb-1">
                  Engine Rationale
                </span>
                <p className="text-xs text-slate-200 leading-relaxed">
                  {selectedSkuDetail.explanation}
                </p>
              </div>

              {/* Preferred vs Alternative Suppliers Comparison */}
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted mb-2.5">
                  Supplier Replenishment Options
                </h4>
                <div className="space-y-2">
                  
                  {/* Preferred */}
                  <div className="p-3 rounded-lg bg-surface-elevated border border-emerald-700/40 flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-ink">{selectedSkuDetail.preferred_supplier_name}</span>
                        <span className="text-[9px] bg-emerald-900/30 text-risk-low px-1.5 py-0.5 rounded font-bold">PREFERRED</span>
                      </div>
                      <span className="text-[11px] text-muted block mt-0.5">
                        Lead Time: {selectedSkuDetail.lead_time_days} days | Risk: {selectedSkuDetail.preferred_supplier_risk_score * 100}% ({selectedSkuDetail.preferred_supplier_risk_tier})
                      </span>
                    </div>
                    <span className="text-xs font-mono font-semibold text-emerald-400">Primary Channel</span>
                  </div>

                  {/* Alternatives */}
                  {selectedSkuDetail.alternative_suppliers.map((alt: any) => (
                    <div key={alt.supplier_id} className="p-3 rounded-lg bg-surface-elevated/60 border border-hairline flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-xs text-slate-300">{alt.supplier_name}</span>
                          <span className="text-[9px] text-muted font-mono">{alt.supplier_id}</span>
                        </div>
                        <span className="text-[11px] text-muted block mt-0.5">
                          Lead Time: {alt.lead_time_days} days | Risk: {alt.risk_score * 100}% ({alt.risk_tier}) | ${alt.estimated_unit_cost}/unit
                        </span>
                        <span className="text-[10px] text-amber-400/90 block mt-0.5">
                          {alt.capacity_status}
                        </span>
                      </div>
                      <span className="text-xs text-muted font-medium">Backup</span>
                    </div>
                  ))}

                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-hairline">
                <button
                  onClick={() => setSelectedSkuDetail(null)}
                  className="btn-secondary !h-8 !text-xs px-4"
                >
                  Close
                </button>
              </div>

            </div>
          </div>
        )}

      </Stagger>
    </div>
  );
}
