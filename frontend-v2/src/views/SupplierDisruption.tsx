import { useState, useEffect } from 'react';
import { 
  AlertOctagon, Play, RotateCcw, ShieldAlert, 
  Package, DollarSign, AlertTriangle, 
  Sparkles, Building2, Truck 
} from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';

import { useRiskContext, useSupplierDisruptionMutation } from '../hooks/useDashboardQueries';
import { GlassCard } from '../components/ui/GlassCard';
import { Stagger, StaggerItem } from '../components/motion/Stagger';
import { ViewSkeleton } from '../components/ui/ViewSkeleton';

export default function SupplierDisruption() {
  const { data: riskContext, isLoading: isLoadingRisk } = useRiskContext();
  const disruptionMutation = useSupplierDisruptionMutation();

  const suppliers = riskContext?.supplier_risks ?? [];

  // Active disruption inputs
  const [selectedSupplierId, setSelectedSupplierId] = useState<string>('');
  const [disruptionType, setDisruptionType] = useState<'SHUTDOWN' | 'DELAY' | 'CAPACITY_CUT'>('SHUTDOWN');
  const [durationDays, setDurationDays] = useState<number>(30);
  const [severityPct, setSeverityPct] = useState<number>(100);

  // Result state
  const [disruptionResult, setDisruptionResult] = useState<any>(null);

  // Initialize selected supplier
  useEffect(() => {
    if (suppliers.length > 0 && !selectedSupplierId) {
      setSelectedSupplierId(suppliers[0].supplier_id);
    }
  }, [suppliers, selectedSupplierId]);

  // Initial simulation
  useEffect(() => {
    if (selectedSupplierId) {
      runDisruption();
    }
  }, [selectedSupplierId]);

  const runDisruption = async () => {
    if (!selectedSupplierId) return;
    try {
      const res = await disruptionMutation.mutateAsync({
        supplier_id: selectedSupplierId,
        disruption_type: disruptionType,
        duration_days: durationDays,
        severity_pct: severityPct,
      });
      setDisruptionResult(res);
    } catch {
      toast.error('Disruption simulation failed.');
    }
  };

  const handleReset = () => {
    setDisruptionType('SHUTDOWN');
    setDurationDays(30);
    setSeverityPct(100);
    runDisruption();
  };

  if (isLoadingRisk && !disruptionResult) {
    return <ViewSkeleton />;
  }

  const res = disruptionResult;

  return (
    <div className="h-full overflow-y-auto p-5 lg:p-6 space-y-6 max-w-content mx-auto">
      <Stagger className="space-y-6">
        
        {/* Header Block */}
        <StaggerItem className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-hairline">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-xl bg-rose-500/10 border border-rose-500/30 text-risk-high">
                <AlertOctagon size={20} />
              </div>
              <h1 className="text-xl font-semibold text-ink">Supplier Disruption & Recovery Simulator</h1>
            </div>
            <p className="text-xs text-body mt-1">
              Stress-test supplier shutdown scenarios, quantify product line exposure, and evaluate mitigation alternatives.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-[11px] font-mono text-muted bg-surface-elevated px-3 py-1.5 rounded-full border border-hairline flex items-center gap-1.5">
              <ShieldAlert size={13} className="text-amber-400" />
              Reversible Scenario Matrix
            </span>
            <button
              onClick={handleReset}
              className="btn-secondary !h-9 text-xs flex items-center gap-1.5"
            >
              <RotateCcw size={13} />
              Reset
            </button>
          </div>
        </StaggerItem>

        {/* Controls Card */}
        <StaggerItem>
          <GlassCard accent="rose" className="p-5">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
              
              {/* Supplier Selector */}
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Select Primary Vendor</label>
                <select
                  value={selectedSupplierId}
                  onChange={(e) => setSelectedSupplierId(e.target.value)}
                  className="w-full bg-slate-900/60 border border-hairline rounded-lg px-3 py-2 text-xs text-ink focus:outline-none focus:border-rose-500"
                >
                  {suppliers.map((s: any) => (
                    <option key={s.supplier_id} value={s.supplier_id}>
                      {s.supplier_name} ({s.supplier_id}) — {((s.risk_score ?? 0) * 100).toFixed(0)}% Risk
                    </option>
                  ))}
                  {suppliers.length === 0 && (
                    <option value="SUP-0001">SUP-0001 (Apex Global)</option>
                  )}
                </select>
                <span className="text-[10px] text-muted mt-1 block">Live supplier network database</span>
              </div>

              {/* Disruption Mode */}
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Disruption Nature</label>
                <div className="grid grid-cols-3 gap-1.5">
                  {(['SHUTDOWN', 'DELAY', 'CAPACITY_CUT'] as const).map((type) => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => setDisruptionType(type)}
                      className={clsx(
                        'py-1.5 text-[11px] font-medium rounded-lg border transition-colors',
                        disruptionType === type
                          ? 'bg-rose-950/60 text-rose-300 border-rose-600/60 font-semibold'
                          : 'bg-surface-elevated text-body border-hairline hover:text-ink'
                      )}
                    >
                      {type === 'SHUTDOWN' ? 'Halt' : type === 'DELAY' ? 'Delay' : 'Capacity'}
                    </button>
                  ))}
                </div>
                <span className="text-[10px] text-muted mt-1 block">
                  {disruptionType === 'SHUTDOWN' ? '100% stop of incoming shipments' :
                   disruptionType === 'DELAY' ? 'Severe logistics transit hold' : 'Partial line throughput loss'}
                </span>
              </div>

              {/* Duration Slider */}
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="text-xs font-medium text-slate-400">Duration (Days)</label>
                  <span className="text-xs font-mono font-bold text-amber-400">{durationDays} days</span>
                </div>
                <input
                  type="range"
                  min="7"
                  max="90"
                  step="7"
                  value={durationDays}
                  onChange={(e) => setDurationDays(parseInt(e.target.value, 10))}
                  className="w-full accent-rose-500 cursor-pointer h-2 bg-slate-800 rounded-lg"
                />
                <div className="flex justify-between text-[10px] text-muted mt-1">
                  <span>1 week</span>
                  <span>30 days</span>
                  <span>90 days</span>
                </div>
              </div>

              {/* Action Button */}
              <div className="flex flex-col justify-end">
                <button
                  onClick={runDisruption}
                  disabled={disruptionMutation.isPending}
                  className="btn-primary !h-9 !text-xs w-full flex items-center justify-center gap-1.5 bg-rose-600 hover:bg-rose-500 text-white"
                >
                  <Play size={13} />
                  {disruptionMutation.isPending ? 'Simulating Impact...' : 'Simulate Disruption Impact'}
                </button>
              </div>

            </div>
          </GlassCard>
        </StaggerItem>

        {/* Simulation Impact Summary */}
        {res && (
          <StaggerItem className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            
            {/* Risk Elevation */}
            <GlassCard className="p-4">
              <div className="flex items-center justify-between text-muted text-xs mb-1">
                <span>Vendor Risk Elevation</span>
                <AlertTriangle size={15} className="text-risk-high" />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono text-risk-high">
                  {((res.disrupted_risk_score ?? 0) * 100).toFixed(0)}%
                </span>
                <span className="text-xs text-muted">
                  vs {((res.baseline_risk_score ?? 0) * 100).toFixed(0)}% base
                </span>
              </div>
              <div className="mt-2 text-[11px] text-muted">
                Status shifts from <span className="uppercase text-slate-300 font-semibold">{res.baseline_risk_tier}</span> to <span className="uppercase text-risk-high font-bold">{res.disrupted_risk_tier}</span>.
              </div>
            </GlassCard>

            {/* Affected SKUs Count */}
            <GlassCard className="p-4">
              <div className="flex items-center justify-between text-muted text-xs mb-1">
                <span>Stockout Vulnerable SKUs</span>
                <Package size={15} />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono text-ink">
                  {res.critical_skus_count}
                </span>
                <span className="text-xs text-muted">of {res.total_affected_skus} dependent SKUs</span>
              </div>
              <div className="mt-2 text-[11px] text-risk-high font-semibold">
                Will run out of inventory before disruption concludes.
              </div>
            </GlassCard>

            {/* Total Shortfall Units */}
            <GlassCard className="p-4">
              <div className="flex items-center justify-between text-muted text-xs mb-1">
                <span>Total Unit Shortfall</span>
                <Truck size={15} />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono text-ink">
                  {res.total_shortfall_units.toLocaleString()}
                </span>
                <span className="text-xs text-muted">units</span>
              </div>
              <div className="mt-2 text-[11px] text-muted">
                Replenishment volume gap over {res.duration_days} days.
              </div>
            </GlassCard>

            {/* Financial Exposure */}
            <GlassCard className="p-4">
              <div className="flex items-center justify-between text-muted text-xs mb-1">
                <span>Value at Risk</span>
                <DollarSign size={15} />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono text-rose-400">
                  ${res.total_inventory_exposure_usd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
              <div className="mt-2 text-[11px] text-muted">
                Unfilled order exposure during outage.
              </div>
            </GlassCard>

          </StaggerItem>
        )}

        {/* Affected SKUs Table & Mitigation Plan */}
        {res && (
          <StaggerItem className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Affected SKUs List */}
            <div className="lg:col-span-2">
              <GlassCard className="!p-0 overflow-hidden">
                <div className="p-4 border-b border-hairline flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-ink flex items-center gap-2">
                    <Package size={16} className="text-accent-indigo" />
                    Dependent SKUs Stockout Runway
                  </h3>
                  <span className="text-xs text-muted font-mono">{res.affected_skus.length} product lines mapped</span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-hairline bg-surface-elevated/40 text-muted uppercase tracking-wider font-semibold text-[10px]">
                        <th className="p-3 pl-4">SKU ID</th>
                        <th className="p-3">On-Hand Units</th>
                        <th className="p-3">Burn Rate</th>
                        <th className="p-3">Runway Days</th>
                        <th className="p-3">Shortfall Units</th>
                        <th className="p-3 pr-4 text-right">Exposure Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-hairline">
                      {res.affected_skus.map((sku: any) => (
                        <tr 
                          key={sku.sku_id}
                          className={clsx(
                            'hover:bg-surface-elevated/40 transition-colors',
                            sku.stockout_expected_within_disruption && 'bg-rose-950/15'
                          )}
                        >
                          <td className="p-3 pl-4 font-mono font-medium text-ink">
                            {sku.sku_id}
                          </td>
                          <td className="p-3 font-mono text-slate-300">
                            {sku.current_units_on_hand.toLocaleString()}
                          </td>
                          <td className="p-3 font-mono text-slate-300">
                            {(sku.daily_consumption ?? 0).toFixed(1)}/day
                          </td>
                          <td className="p-3 font-mono">
                            <span className={clsx(
                              'font-bold',
                              sku.stockout_expected_within_disruption ? 'text-risk-high' : 'text-risk-low'
                            )}>
                              {sku.days_of_stock_remaining}d
                            </span>
                            {sku.stockout_expected_within_disruption && (
                              <span className="text-[10px] text-rose-400 block font-sans">
                                Out on Day {sku.stockout_day}
                              </span>
                            )}
                          </td>
                          <td className="p-3 font-mono">
                            {sku.projected_shortfall_units > 0 ? (
                              <span className="text-rose-400 font-semibold">
                                -{sku.projected_shortfall_units.toLocaleString()}
                              </span>
                            ) : (
                              <span className="text-muted">—</span>
                            )}
                          </td>
                          <td className="p-3 pr-4 text-right font-mono font-semibold text-slate-200">
                            ${sku.estimated_value_exposure_usd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </GlassCard>
            </div>

            {/* Candidate Alternatives & Suggested Mitigations */}
            <div className="space-y-6">
              
              {/* Alternatives List */}
              <GlassCard className="p-4">
                <h3 className="text-sm font-semibold text-ink flex items-center gap-2 mb-3">
                  <Building2 size={16} className="text-cyan-400" />
                  Qualified Alternative Vendors
                </h3>
                <div className="space-y-2.5">
                  {res.alternative_candidates.map((alt: any) => (
                    <div key={alt.supplier_id} className="p-3 rounded-lg bg-surface-elevated/70 border border-hairline">
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="font-semibold text-slate-200">{alt.supplier_name}</span>
                        <span className={clsx(
                          'text-[10px] font-mono px-1.5 py-0.5 rounded font-bold uppercase',
                          alt.risk_score < 0.35 ? 'bg-emerald-900/30 text-risk-low' : 'bg-amber-900/30 text-risk-medium'
                        )}>
                          {((alt.risk_score ?? 0) * 100).toFixed(0)}% Risk
                        </span>
                      </div>
                      <div className="text-[11px] text-muted flex justify-between">
                        <span>Lead Time: {alt.lead_time_days} days</span>
                        <span>Est: ${alt.estimated_unit_cost}/unit</span>
                      </div>
                      <span className="text-[10px] text-amber-400/90 block mt-1 font-medium">
                        {alt.capacity_status}
                      </span>
                    </div>
                  ))}
                </div>
              </GlassCard>

              {/* Action Plan */}
              <GlassCard className="p-4">
                <h3 className="text-sm font-semibold text-ink flex items-center gap-2 mb-3">
                  <Sparkles size={16} className="text-amber-400" />
                  Recommended Recovery Protocols
                </h3>
                <div className="space-y-3">
                  {res.recommended_mitigations.map((rec: any, idx: number) => (
                    <div key={idx} className="p-3 rounded-lg bg-accent-indigo/10 border border-accent-indigo/30">
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="font-semibold text-slate-200">{rec.title}</span>
                        <span className="text-[9px] bg-accent-indigo text-white px-1.5 py-0.5 rounded font-bold uppercase">
                          {rec.priority}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-300 leading-relaxed mb-1.5">
                        {rec.description}
                      </p>
                      <div className="text-[10px] text-muted border-t border-hairline/60 pt-1 flex justify-between">
                        <span className="text-emerald-400 font-medium">{rec.estimated_risk_mitigation}</span>
                        <span className="text-slate-400">{rec.trade_off}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </GlassCard>

            </div>

          </StaggerItem>
        )}

      </Stagger>
    </div>
  );
}
