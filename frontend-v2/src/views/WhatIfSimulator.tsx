import { useState, useEffect } from 'react';
import { 
  SlidersHorizontal, RotateCcw, AlertTriangle, 
  TrendingUp, Clock, Package, Play, Info, ArrowRight, Sparkles 
} from 'lucide-react';
import { 
  ResponsiveContainer, ComposedChart, Line, Area, XAxis, YAxis, 
  CartesianGrid, Tooltip as RechartsTooltip, ReferenceLine 
} from 'recharts';
import clsx from 'clsx';
import toast from 'react-hot-toast';

import { useInventory, useWhatIfMutation } from '../hooks/useDashboardQueries';
import { GlassCard } from '../components/ui/GlassCard';
import { Stagger, StaggerItem } from '../components/motion/Stagger';
import { ViewSkeleton } from '../components/ui/ViewSkeleton';

export default function WhatIfSimulator() {
  const { data: inventorySkus = [], isLoading: isLoadingInventory } = useInventory();
  const whatIfMutation = useWhatIfMutation();

  // Active controls
  const [selectedSku, setSelectedSku] = useState('FOODS_1_001_CA_1_evaluation');
  const [demandPct, setDemandPct] = useState<number>(20);
  const [leadTimeIncrease, setLeadTimeIncrease] = useState<number>(10);
  const [inventoryOverride, setInventoryOverride] = useState<string>('');
  const [disruptionPct, setDisruptionPct] = useState<number>(0);

  // Result state
  const [simulationResult, setSimulationResult] = useState<any>(null);

  // Initialize selected SKU when inventory data loads
  useEffect(() => {
    if (inventorySkus.length > 0 && !selectedSku) {
      setSelectedSku(inventorySkus[0].sku_id);
    }
  }, [inventorySkus, selectedSku]);

  // Initial simulation run
  useEffect(() => {
    if (selectedSku) {
      runSimulation();
    }
  }, [selectedSku]);

  const runSimulation = async () => {
    try {
      const res = await whatIfMutation.mutateAsync({
        sku_id: selectedSku,
        demand_change_pct: demandPct,
        lead_time_increase_days: leadTimeIncrease,
        inventory_override: inventoryOverride ? parseInt(inventoryOverride, 10) : undefined,
        supplier_disruption_pct: disruptionPct,
      });
      setSimulationResult(res);
    } catch {
      toast.error('Simulation failed. Please check inputs.');
    }
  };

  const handleReset = () => {
    setDemandPct(0);
    setLeadTimeIncrease(0);
    setInventoryOverride('');
    setDisruptionPct(0);
    whatIfMutation.mutate(
      {
        sku_id: selectedSku,
        demand_change_pct: 0,
        lead_time_increase_days: 0,
        supplier_disruption_pct: 0,
      },
      {
        onSuccess: (data) => {
          setSimulationResult(data);
          toast.success('Reset to baseline conditions');
        },
      }
    );
  };

  if (isLoadingInventory && !simulationResult) {
    return <ViewSkeleton />;
  }

  const res = simulationResult;

  return (
    <div className="h-full overflow-y-auto p-5 lg:p-6 space-y-6 max-w-content mx-auto">
      <Stagger className="space-y-6">
        
        {/* Header Block */}
        <StaggerItem className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-hairline">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-xl bg-accent-indigo/10 border border-accent-indigo/30 text-accent-indigo">
                <SlidersHorizontal size={20} />
              </div>
              <h1 className="text-xl font-semibold text-ink">Supply-Chain What-If Simulator</h1>
            </div>
            <p className="text-xs text-body mt-1">
              Evaluate hypothetical demand surges, supplier transit delays, and capacity reductions in real-time.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-muted bg-surface-elevated px-3 py-1.5 rounded-full border border-hairline flex items-center gap-1.5">
              <Info size={13} className="text-accent-indigo" />
              Transparent Scenario Heuristic (Zero Re-Training)
            </span>
            <button
              onClick={handleReset}
              className="btn-secondary !min-h-[44px] text-xs flex items-center gap-1.5 touch-action-manipulation px-4"
              title="Reset sliders to 0 delta baseline"
            >
              <RotateCcw size={14} />
              Reset Baseline
            </button>
          </div>
        </StaggerItem>

        {/* Controls Grid */}
        <StaggerItem>
          <GlassCard accent="indigo" className="p-5">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-5">
              
              {/* SKU Selection */}
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Target SKU</label>
                <select
                  value={selectedSku}
                  onChange={(e) => setSelectedSku(e.target.value)}
                  className="w-full bg-slate-900/60 border border-hairline rounded-lg px-3 py-2 text-xs text-ink focus:outline-none focus:border-accent-indigo"
                >
                  {inventorySkus.map((sku: any) => (
                    <option key={sku.sku_id} value={sku.sku_id}>
                      {sku.sku_id} ({sku.status})
                    </option>
                  ))}
                  {inventorySkus.length === 0 && (
                    <option value="FOODS_1_001_CA_1_evaluation">FOODS_1_001_CA_1_evaluation</option>
                  )}
                </select>
                <span className="text-[10px] text-muted mt-1 block">TFT 14-day demand source</span>
              </div>

              {/* Demand Surge Slider */}
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="text-xs font-medium text-slate-400">Demand Change</label>
                  <span className={clsx(
                    'text-xs font-mono font-semibold',
                    demandPct > 0 ? 'text-rose-400' : demandPct < 0 ? 'text-emerald-400' : 'text-slate-300'
                  )}>
                    {demandPct > 0 ? `+${demandPct}%` : `${demandPct}%`}
                  </span>
                </div>
                <input
                  type="range"
                  min="-50"
                  max="100"
                  step="5"
                  value={demandPct}
                  onChange={(e) => setDemandPct(parseInt(e.target.value, 10))}
                  className="w-full accent-accent-indigo cursor-pointer h-2 bg-slate-800 rounded-lg"
                />
                <div className="flex justify-between text-[10px] text-muted mt-1">
                  <span>-50% slump</span>
                  <span>Baseline</span>
                  <span>+100% surge</span>
                </div>
              </div>

              {/* Lead-Time Increase Slider */}
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="text-xs font-medium text-slate-400">Lead-Time Delay</label>
                  <span className={clsx(
                    'text-xs font-mono font-semibold',
                    leadTimeIncrease > 0 ? 'text-amber-400' : 'text-slate-300'
                  )}>
                    +{leadTimeIncrease} days
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="45"
                  step="1"
                  value={leadTimeIncrease}
                  onChange={(e) => setLeadTimeIncrease(parseInt(e.target.value, 10))}
                  className="w-full accent-accent-indigo cursor-pointer h-2 bg-slate-800 rounded-lg"
                />
                <div className="flex justify-between text-[10px] text-muted mt-1">
                  <span>0d (Normal)</span>
                  <span>+20d</span>
                  <span>+45d severe</span>
                </div>
              </div>

              {/* Disruption Severity Slider */}
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="text-xs font-medium text-slate-400">Disruption Severity</label>
                  <span className={clsx(
                    'text-xs font-mono font-semibold',
                    disruptionPct > 0 ? 'text-rose-400' : 'text-slate-300'
                  )}>
                    {disruptionPct}% capacity cut
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="10"
                  value={disruptionPct}
                  onChange={(e) => setDisruptionPct(parseInt(e.target.value, 10))}
                  className="w-full accent-accent-indigo cursor-pointer h-2 bg-slate-800 rounded-lg"
                />
                <div className="flex justify-between text-[10px] text-muted mt-1">
                  <span>0%</span>
                  <span>50% partial</span>
                  <span>100% halt</span>
                </div>
              </div>

              {/* Inventory Override & Action Button */}
              <div className="flex flex-col justify-between">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Inventory Override (Units)</label>
                  <input
                    type="number"
                    placeholder="Auto (Live on-hand)"
                    value={inventoryOverride}
                    onChange={(e) => setInventoryOverride(e.target.value)}
                    className="w-full bg-slate-900/60 border border-hairline rounded-lg px-3 py-1.5 text-xs text-ink focus:outline-none focus:border-accent-indigo"
                  />
                </div>
                <button
                  onClick={runSimulation}
                  disabled={whatIfMutation.isPending}
                  className="btn-primary !min-h-[44px] !text-xs w-full flex items-center justify-center gap-2 mt-2 font-semibold touch-action-manipulation"
                >
                  <Play size={14} />
                  {whatIfMutation.isPending ? 'Simulating...' : 'Recalculate Scenario'}
                </button>
              </div>

            </div>
          </GlassCard>
        </StaggerItem>

        {/* Comparison KPI Grid */}
        {res && (
          <StaggerItem className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            
            {/* Days to Stockout */}
            <GlassCard className="p-4">
              <div className="flex items-center justify-between text-muted text-xs mb-1">
                <span>Inventory Coverage</span>
                <Clock size={15} />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono text-ink">
                  {res.simulated_days_to_stockout}d
                </span>
                <span className="text-xs text-muted">
                  vs {res.baseline_days_to_stockout}d base
                </span>
              </div>
              <div className="mt-2 text-[11px] font-mono flex items-center gap-1">
                <span className={clsx(
                  'px-1.5 py-0.5 rounded font-semibold',
                  res.delta_days_to_stockout < 0 ? 'bg-rose-900/30 text-risk-high' : 'bg-emerald-900/30 text-risk-low'
                )}>
                  {res.delta_days_to_stockout > 0 ? `+${res.delta_days_to_stockout}d` : `${res.delta_days_to_stockout}d`}
                </span>
                <span className="text-muted">runway shift</span>
              </div>
            </GlassCard>

            {/* Stockout Risk Tier */}
            <GlassCard className="p-4">
              <div className="flex items-center justify-between text-muted text-xs mb-1">
                <span>Stockout Vulnerability</span>
                <AlertTriangle size={15} />
              </div>
              <div className="flex items-center gap-2">
                <span className={clsx(
                  'text-xs font-bold px-2.5 py-1 rounded-full uppercase border',
                  res.simulated_risk_tier === 'CRITICAL' ? 'bg-rose-900/30 text-risk-high border-rose-700/50' :
                  res.simulated_risk_tier === 'ELEVATED' ? 'bg-amber-900/30 text-risk-medium border-amber-700/50' :
                  'bg-emerald-900/30 text-risk-low border-emerald-700/50'
                )}>
                  {res.simulated_risk_tier} RISK
                </span>
                <ArrowRight size={12} className="text-muted" />
                <span className="text-[11px] text-muted uppercase">Base: {res.baseline_risk_tier}</span>
              </div>
              <div className="mt-2 text-[11px] text-muted">
                {res.is_stockout_within_replenishment ? (
                  <span className="text-risk-high font-semibold">⚠️ Stockout occurs BEFORE replenishment arrives</span>
                ) : (
                  <span>Sufficient buffer runway for normal reorder</span>
                )}
              </div>
            </GlassCard>

            {/* Reorder Point (ROP) */}
            <GlassCard className="p-4">
              <div className="flex items-center justify-between text-muted text-xs mb-1">
                <span>Simulated Reorder Point</span>
                <TrendingUp size={15} />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono text-ink">
                  {res.simulated_reorder_point.toLocaleString()}
                </span>
                <span className="text-xs text-muted">units</span>
              </div>
              <div className="mt-2 text-[11px] text-muted">
                Base ROP was {res.baseline_reorder_point.toLocaleString()} units ({res.simulated_reorder_point - res.baseline_reorder_point > 0 ? `+${(res.simulated_reorder_point - res.baseline_reorder_point).toLocaleString()}` : '0'} buffer delta).
              </div>
            </GlassCard>

            {/* Effective Lead Time */}
            <GlassCard className="p-4">
              <div className="flex items-center justify-between text-muted text-xs mb-1">
                <span>Effective Lead Time</span>
                <Package size={15} />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono text-ink">
                  {res.simulated_effective_lead_time_days}d
                </span>
                <span className="text-xs text-muted">
                  vs {res.baseline_lead_time_days}d base
                </span>
              </div>
              <div className="mt-2 text-[11px] text-muted">
                Supplier: <span className="text-slate-300 font-medium">{res.supplier_name}</span>
              </div>
            </GlassCard>

          </StaggerItem>
        )}

        {/* 30-Day Trajectory Projection & Driver Attribution */}
        {res && (
          <StaggerItem className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Chart Block */}
            <div className="lg:col-span-2">
              <GlassCard accent="indigo" className="p-5">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-sm font-semibold text-ink flex items-center gap-2">
                      <TrendingUp size={16} className="text-accent-indigo" />
                      30-Day Inventory Depletion Trajectory
                    </h3>
                    <p className="text-xs text-muted mt-0.5">
                      Comparing baseline demand burn rate against the simulated shock scenario.
                    </p>
                  </div>
                  {res.stockout_day && (
                    <span className="text-xs bg-rose-900/30 text-risk-high border border-rose-700/40 px-2.5 py-1 rounded-full font-mono font-medium">
                      Simulated Stockout: Day {res.stockout_day}
                    </span>
                  )}
                </div>

                <div className="h-[320px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={res.trajectory} margin={{ top: 10, right: 10, bottom: 10, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" />
                      <XAxis dataKey="day" unit="d" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                      <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                      <RechartsTooltip
                        contentStyle={{
                          background: '#0f172a',
                          border: '1px solid rgba(148,163,184,0.2)',
                          borderRadius: 12,
                          fontSize: 12,
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="baseline_inventory"
                        name="Baseline On-Hand"
                        stroke="#06b6d4"
                        fill="#06b6d4"
                        fillOpacity={0.08}
                        strokeWidth={2}
                      />
                      <Line
                        type="monotone"
                        dataKey="simulated_inventory"
                        name="Simulated Scenario"
                        stroke="#f43f5e"
                        strokeWidth={2.5}
                        dot={false}
                      />
                      {res.stockout_day && (
                        <ReferenceLine
                          x={res.stockout_day}
                          stroke="#f43f5e"
                          strokeDasharray="4 4"
                          label={{ value: `Stockout: Day ${res.stockout_day}`, fill: '#f43f5e', fontSize: 11, position: 'top' }}
                        />
                      )}
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>

                <div className="flex items-center justify-center gap-6 mt-3 text-xs text-muted">
                  <span className="flex items-center gap-2">
                    <span className="w-3 h-0.5 bg-cyan-400" /> Baseline Trajectory
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="w-3 h-0.5 bg-rose-500" /> Simulated Trajectory
                  </span>
                </div>
              </GlassCard>
            </div>

            {/* Driver Breakdown & Explanation Card */}
            <div>
              <GlassCard className="p-5 h-full flex flex-col justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-ink flex items-center gap-2 mb-1">
                    <Sparkles size={16} className="text-amber-400" />
                    Assumption Impact Attribution
                  </h3>
                  <p className="text-xs text-muted mb-4">
                    Transparent ranking of what caused the largest runway delta.
                  </p>

                  <div className="space-y-3">
                    {res.drivers.map((d: any, idx: number) => (
                      <div key={idx} className="p-3 rounded-lg bg-surface-elevated/70 border border-hairline">
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="font-semibold text-slate-200">{d.factor}</span>
                          <span className={clsx(
                            'font-mono font-bold text-xs',
                            d.impact_days < 0 ? 'text-rose-400' : 'text-emerald-400'
                          )}>
                            {d.impact_days > 0 ? `+${d.impact_days}d` : `${d.impact_days}d`}
                          </span>
                        </div>
                        <p className="text-[11px] text-muted leading-relaxed">{d.description}</p>
                      </div>
                    ))}

                    {res.drivers.length === 0 && (
                      <p className="text-xs text-muted italic">No active shock parameters entered.</p>
                    )}
                  </div>
                </div>

                {/* Primary Narrative Summary */}
                <div className="mt-4 p-3 rounded-lg bg-accent-indigo/10 border border-accent-indigo/30">
                  <span className="text-[10px] uppercase font-bold text-accent-indigo tracking-wider block mb-1">
                    Simulator Synthesis
                  </span>
                  <p className="text-xs text-slate-200 leading-relaxed">
                    {res.primary_driver_explanation}
                  </p>
                </div>
              </GlassCard>
            </div>

          </StaggerItem>
        )}

      </Stagger>
    </div>
  );
}
