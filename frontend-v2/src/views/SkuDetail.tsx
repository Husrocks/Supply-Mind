import { useParams, useNavigate } from 'react-router-dom';
import { useSkuDetail } from '../hooks/useDashboardQueries';
import { 
  ArrowLeft, AlertCircle, Package, Activity, 
  TrendingUp, Truck, ShieldAlert, ArrowRight 
} from 'lucide-react';
import { 
  ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis, 
  CartesianGrid, Tooltip as RechartsTooltip 
} from 'recharts';
import clsx from 'clsx';
import { GlassCard } from '../components/ui/GlassCard';
import { ViewSkeleton } from '../components/ui/ViewSkeleton';
import { RadialGauge } from '../components/ui/RadialGauge';
import { Stagger, StaggerItem } from '../components/motion/Stagger';
import { RiskContextSimulator } from '../components/widgets/RiskContextSimulator';
import { riskScoreColor } from '../utils/risk';
import { usePrefersReducedMotion } from '../hooks/usePrefersReducedMotion';

export function SkuDetail() {
  const { sku_id } = useParams<{ sku_id: string }>();
  const navigate = useNavigate();
  const reduced = usePrefersReducedMotion();
  const { data, isLoading, isError } = useSkuDetail(sku_id ?? '');

  if (isLoading) {
    return <ViewSkeleton />;
  }

  if (isError || !data) {
    return (
      <div className="p-8 flex flex-col items-center gap-4 glass-card max-w-lg mx-auto mt-12">
        <AlertCircle className="text-risk-high" size={32} />
        <p className="text-sm text-body text-center">Unable to load details for SKU "{sku_id}". Ensure it exists in the demand forecasting logs.</p>
        <button onClick={() => navigate('/inventory')} className="btn-secondary !h-9 text-xs flex items-center gap-1.5">
          <ArrowLeft size={12} /> Back to Inventory Heatmap
        </button>
      </div>
    );
  }

  const safetyBuffer = Math.min(100, (data.days_to_stockout / 28) * 100);

  return (
    <div className="h-full overflow-y-auto p-5 lg:p-6">
      <Stagger className="max-w-[1400px] mx-auto space-y-6">
        
        {/* Header Block */}
        <StaggerItem className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-hairline">
          <div className="flex items-center gap-3">
            <button 
              onClick={() => navigate('/inventory')} 
              className="p-2 hover:bg-slate-800/80 rounded-full text-muted hover:text-ink transition-colors focus:ring-1 focus:ring-accent-indigo focus:outline-none"
              title="Back"
            >
              <ArrowLeft size={18} />
            </button>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-semibold text-ink">{sku_id}</h1>
                <span className="text-xs bg-slate-800/80 px-2.5 py-0.5 rounded-full border border-hairline text-muted uppercase">
                  Category: {(sku_id ?? '').split('_')[0]}
                </span>
              </div>
              <p className="text-xs text-body mt-1.5">Model: Temporal Fusion Transformer (TFT) 14-day forecasts</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <span className={clsx(
              'text-xs font-semibold px-3 py-1 rounded-full border border-hairline uppercase',
              data.status === 'CRITICAL' ? 'bg-rose-900/20 text-risk-high border-rose-700/30' :
              data.status === 'ELEVATED' ? 'bg-amber-900/20 text-risk-medium border-amber-700/30' :
              'bg-emerald-900/20 text-risk-low border-emerald-700/30'
            )}>{data.status} RISK</span>
          </div>
        </StaggerItem>

        {/* SKU KPI Summary Grid */}
        <StaggerItem className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <GlassCard accent="indigo" className="flex justify-between items-center py-5">
            <div>
              <p className="text-[10px] text-muted uppercase tracking-wider">Days to Stockout</p>
              <h3 className="text-3xl font-mono tabular-nums font-semibold mt-1 text-ink">
                {data.days_to_stockout} days
              </h3>
            </div>
          </GlassCard>

          <GlassCard accent="cyan" className="flex justify-between items-center py-5">
            <div>
              <p className="text-[10px] text-muted uppercase tracking-wider">Current Inventory</p>
              <h3 className="text-3xl font-mono tabular-nums font-semibold mt-1 text-ink">
                {data.current_inventory.toLocaleString()} units
              </h3>
            </div>
            <Package size={24} className="text-accent-cyan opacity-80" />
          </GlassCard>

          <GlassCard accent="emerald" className="flex justify-between items-center py-5">
            <div>
              <p className="text-[10px] text-muted tracking-wider uppercase">Safety Buffer</p>
              <h3 className="text-3xl font-mono tabular-nums font-semibold mt-1 text-ink">
                {safetyBuffer.toFixed(0)}%
              </h3>
            </div>
            <RadialGauge value={safetyBuffer} size={50} accent="emerald" label="" />
          </GlassCard>

          <GlassCard accent="rose" className="flex justify-between items-center py-5">
            <div>
              <p className="text-[10px] text-muted tracking-wider uppercase">Uncertainty Spread</p>
              <h3 className="text-3xl font-mono tabular-nums font-semibold mt-1 text-ink">
                {data.uncertainty_spread} units
              </h3>
            </div>
            <Activity size={20} className="text-risk-high opacity-85" />
          </GlassCard>
        </StaggerItem>

        {/* Forecast Chart */}
        <StaggerItem>
          <GlassCard accent="indigo">
            <h3 className="text-sm font-semibold text-ink uppercase tracking-wider mb-4 border-b border-hairline pb-2 flex items-center gap-2">
              <TrendingUp size={16} className="text-accent-indigo" /> TFT Quantile Demand Forecast
            </h3>
            <div className="h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={data.forecast_history} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" />
                  <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 10 }} minTickGap={28} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <RechartsTooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 12 }} />
                  <Area type="monotone" dataKey="p95" fill="#6366f1" fillOpacity={0.12} stroke="none" isAnimationActive={!reduced} />
                  <Area type="monotone" dataKey="p05" fill="#020617" stroke="none" isAnimationActive={!reduced} />
                  <Line type="monotone" dataKey="actual" stroke="#10b981" strokeWidth={2.5} dot={{ r: 3 }} isAnimationActive={!reduced} name="Actual demand" />
                  <Line type="monotone" dataKey="p50" stroke="#6366f1" strokeDasharray="4 4" strokeWidth={2.5} dot={false} isAnimationActive={!reduced} name="P50 forecast" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-wrap gap-4 justify-center text-xs mt-3 text-muted">
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-emerald-500 rounded-full" /> Actual Sales</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-indigo-500 rounded-full" /> P50 Median Forecast</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-indigo-500/25 rounded" /> P05–P95 Confidence Band</span>
            </div>
          </GlassCard>
        </StaggerItem>

        {/* Risk Context Simulator */}
        <StaggerItem>
          <RiskContextSimulator 
            skuId={sku_id ?? ''}
            defaultSupplierId={data.supplier_dependencies?.[0]?.supplier_id}
            defaultInventory={data.current_inventory}
            availableSuppliers={data.supplier_dependencies || []}
          />
        </StaggerItem>

        {/* Bottom Panel: Actions and Dependencies */}
        <StaggerItem className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          
          {/* Supplier Dependencies */}
          <GlassCard accent="cyan" className="!p-0 overflow-hidden">
            <div className="p-5 pb-3 border-b border-hairline">
              <h3 className="text-sm font-semibold text-ink uppercase tracking-wider flex items-center gap-2">
                <Truck size={16} className="text-accent-cyan" /> Supplier Dependencies
              </h3>
            </div>
            <div className="p-4 space-y-4 max-h-[300px] overflow-y-auto">
              {data.supplier_dependencies && data.supplier_dependencies.length > 0 ? (
                data.supplier_dependencies.map((dep: any, idx: number) => {
                  const percent = dep.volume;
                  return (
                    <div 
                      key={idx} 
                      className="p-3 border border-hairline rounded-xl hover:bg-slate-800/10 transition-colors cursor-pointer flex justify-between items-center"
                      onClick={() => navigate(`/supplier/${dep.supplier_id}`)}
                    >
                      <div className="flex-1">
                        <div className="flex justify-between items-center text-xs text-ink font-medium mb-1.5">
                          <span className="hover:text-accent-cyan transition-colors">{dep.supplier_name}</span>
                          <span className="font-mono text-muted">{percent}% Share</span>
                        </div>
                        <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-accent-cyan"
                            style={{ width: `${percent}%` }}
                          />
                        </div>
                      </div>
                      <div className="ml-3 shrink-0 flex items-center gap-1.5">
                        <span className="text-[10px] font-semibold font-mono" style={{ color: riskScoreColor(dep.risk_score) }}>
                          {(dep.risk_score * 100).toFixed(0)}% Risk
                        </span>
                        <ArrowRight size={12} className="text-muted" />
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="p-8 text-center text-xs text-muted italic">
                  No supplier dependencies recorded.
                </div>
              )}
            </div>
          </GlassCard>

          {/* Action Log for this SKU */}
          <GlassCard accent="rose" className="!p-0 overflow-hidden">
            <div className="p-5 pb-3 border-b border-hairline">
              <h3 className="text-sm font-semibold text-ink uppercase tracking-wider flex items-center gap-2">
                <ShieldAlert size={16} className="text-risk-high" /> Mitigation Logs
              </h3>
            </div>
            <div className="max-h-[300px] overflow-y-auto">
              {data.actions && data.actions.length > 0 ? (
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-hairline text-muted">
                      <th className="px-5 py-3 font-semibold">Action</th>
                      <th className="px-4 py-3 font-semibold">Status</th>
                      <th className="px-4 py-3 font-semibold">Cost</th>
                      <th className="px-5 py-3 font-semibold">Executed On</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.actions.map((a: any) => (
                      <tr key={a.action_id} className="border-b border-hairline hover:bg-slate-800/20">
                        <td className="px-5 py-3">
                          <div className="font-semibold text-ink">{a.action_type.replace(/_/g, ' ')}</div>
                          <div className="text-[9px] text-muted">{a.supplier_id}</div>
                        </td>
                        <td className="px-4 py-3">
                          <span className={clsx(
                            'font-medium uppercase text-[9px]',
                            a.status === 'executed' || a.status === 'approved' ? 'text-risk-low' :
                            a.status === 'rejected' ? 'text-risk-high' : 'text-risk-medium'
                          )}>{a.status}</span>
                        </td>
                        <td className="px-4 py-3 font-mono tabular-nums">
                          {a.estimated_impact?.cost_delta ? `$${a.estimated_impact.cost_delta.toLocaleString()}` : '—'}
                        </td>
                        <td className="px-5 py-3 text-muted">
                          {new Date(a.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="p-8 text-center text-xs text-muted italic">
                  No mitigation actions logged for this SKU.
                </div>
              )}
            </div>
          </GlassCard>

        </StaggerItem>
      </Stagger>
    </div>
  );
}

export default SkuDetail;
